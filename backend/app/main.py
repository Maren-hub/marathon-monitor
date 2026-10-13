from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from .campus_route import CampusRouteError, MAX_ROUTE_FILE_BYTES, load_course, save_course_geojson
from .export_bundle import create_export_bundle
from .model_import import JOBS as MODEL_JOBS, MAX_ARCHIVE_BYTES, ModelImportError, list_models, model_asset, new_import_path, register_uploaded_job, start_import
from .processing_pipeline import automatic_pipeline
from .pipeline_schemas import PipelineIngestRequest, PipelineIngestResponse, SegmentFusionResult
from .schemas import AlertActionRequest, PlatformSnapshot, SimulationControlRequest, SimulationEventRequest
from .simulation import MarathonSimulation
from .spreadsheet_import import MAX_UPLOAD_BYTES, SpreadsheetImportError, parse_uploaded_table


class LiveConnectionHub:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        disconnected: list[WebSocket] = []
        for connection in list(self.connections):
            try:
                await connection.send_json(payload)
            except Exception:
                disconnected.append(connection)
        for connection in disconnected:
            self.disconnect(connection)


simulation = MarathonSimulation()
hub = LiveConnectionHub()
campus_route_lock = asyncio.Lock()
DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
TECHNICAL_DOCS = {
    "architecture": "architecture.md",
    "pipeline": "自动数据处理管道_V0.1.md",
    "campus-route": "校园路线GeoJSON接入说明.md",
    "model-import": "三维模型导入说明.md",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop_event = asyncio.Event()
    simulator_task = asyncio.create_task(simulation.run(hub.broadcast, stop_event))
    yield
    stop_event.set()
    await simulator_task


app = FastAPI(
    title="马拉松智能监控平台 API",
    description="三维赛道、无人机、穿戴设备与分段监测任务的原型接口。",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "marathon-monitor-api"}


@app.get("/api/campus-route")
async def get_campus_route() -> dict:
    """Read the team-drawn campus route overlay, if one has been imported."""
    async with campus_route_lock:
        return load_course()


@app.post("/api/campus-route/import")
async def import_campus_route(request: Request, kind: Literal["route", "sites"], filename: str) -> dict:
    """Import WGS84 GeoJSON route lines or optional support-site points."""
    if not filename.lower().endswith((".geojson", ".json")):
        raise HTTPException(status_code=422, detail="请选择 .geojson 文件")
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_ROUTE_FILE_BYTES:
            raise HTTPException(status_code=413, detail="GeoJSON 文件超过 2 MB 上限")
    try:
        async with campus_route_lock:
            return save_course_geojson(bytes(content), kind, filename)
    except CampusRouteError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/models")
async def get_models() -> dict:
    """List models that have usable 3D Tiles manifests."""
    return {"models": list_models()}


@app.post("/api/models/import")
async def import_model(request: Request, filename: str) -> dict:
    """Stream a model ZIP to disk, then unpack/convert it in the background."""
    origin = request.headers.get("origin")
    local_origins = {
        "http://127.0.0.1:5173", "http://localhost:5173",
        "http://127.0.0.1:8000", "http://localhost:8000",
    }
    if (origin and origin not in local_origins) or request.headers.get("cf-connecting-ip"):
        raise HTTPException(status_code=403, detail="大模型导入只允许在本机网页操作，请关闭临时分享后再上传")
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=422, detail="请选择 .zip 压缩包")
    try:
        declared_size = int(request.headers.get("content-length", "0") or "0")
    except ValueError:
        raise HTTPException(status_code=400, detail="文件长度信息无效") from None
    if declared_size > MAX_ARCHIVE_BYTES:
        raise HTTPException(status_code=413, detail="模型压缩包超过 12 GB 上限")
    if any(job["stage"] not in {"ready", "error"} for job in MODEL_JOBS.values()):
        raise HTTPException(status_code=409, detail="已有模型正在导入，请等待完成")
    job_id, target = new_import_path()
    received = 0
    try:
        with target.open("wb") as output:
            async for chunk in request.stream():
                received += len(chunk)
                if received > MAX_ARCHIVE_BYTES:
                    raise HTTPException(status_code=413, detail="模型压缩包超过 12 GB 上限")
                output.write(chunk)
        if not received:
            raise HTTPException(status_code=422, detail="压缩包为空")
    except BaseException:
        target.unlink(missing_ok=True)
        target.parent.rmdir()
        raise
    job = register_uploaded_job(job_id, filename)
    asyncio.create_task(start_import(target, filename))
    return {"job": job}


@app.get("/api/models/jobs/{job_id}")
async def get_model_job(job_id: str) -> dict:
    job = MODEL_JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="处理记录不存在；若服务重启，请查看模型列表")
    return {"job": job}


@app.get("/api/models/assets/{model_id}/{asset_path:path}")
async def get_model_asset(model_id: str, asset_path: str) -> FileResponse:
    try:
        path = model_asset(model_id, asset_path)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return FileResponse(path)


@app.get("/api/pipeline/rules")
async def get_pipeline_rules() -> dict:
    """查看当前自动处理规则、权重、版本和原型声明。"""
    return automatic_pipeline.rules()


@app.post("/api/pipeline/ingest", response_model=PipelineIngestResponse)
async def ingest_pipeline_data(request: PipelineIngestRequest) -> PipelineIngestResponse:
    """统一接收手环、无人机、环境和 GIS 数据并自动处理。"""
    return await automatic_pipeline.ingest(request)


@app.post("/api/pipeline/import-file")
async def import_pipeline_file(
    request: Request,
    filename: str,
    default_status: Literal["模拟", "公开", "实测"] = "模拟",
    expected_kind: Literal["wearable", "uav", "environment", "gis_segments"] | None = None,
) -> dict:
    """Read an Excel/CSV file and commit only if every recognised row validates."""
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail={"message": "文件超过 6 MB 上限", "issues": []})
    try:
        parsed, sheets = parse_uploaded_table(filename, bytes(content), default_status)
    except SpreadsheetImportError as error:
        raise HTTPException(status_code=422, detail={"message": str(error), "issues": error.issues}) from error
    if expected_kind is not None:
        detected = {item["kind"] for item in sheets if item.get("rows", 0) > 0}
        if detected != {expected_kind}:
            labels = {
                "wearable": "手环体征",
                "uav": "无人机观测",
                "environment": "环境信息",
                "gis_segments": "赛段GIS",
            }
            found = "、".join(labels.get(item, item) for item in sorted(detected)) or "未识别"
            raise HTTPException(
                status_code=422,
                detail={
                    "message": f"当前模块只接收{labels[expected_kind]}数据，本文件识别为：{found}",
                    "issues": ["请使用本模块模板整理字段，或回到数据总览导入包含多类工作表的完整文件。"],
                },
            )
    ingested = await automatic_pipeline.ingest(parsed)
    return {
        "filename": filename,
        "sheets": sheets,
        "accepted": ingested.accepted,
        "stored": ingested.stored,
        "results": [result.model_dump(mode="json") for result in ingested.results],
        "usable_segments": sorted({result.segment_id for result in ingested.results if result.record_status == "usable"}),
        "partial_segments": [
            {"segment_id": result.segment_id, "missing_sources": result.missing_sources}
            for result in ingested.results if result.record_status == "partial"
        ],
    }


@app.get("/api/pipeline/segments", response_model=list[SegmentFusionResult])
async def get_pipeline_segments() -> list[SegmentFusionResult]:
    """读取已经完成融合、风险计算和任务推荐的赛段结果。"""
    return await automatic_pipeline.results()


@app.get("/api/pipeline/status")
async def get_pipeline_status() -> dict:
    """读取数据管理页所需的汇总状态，不返回个人原始记录。"""
    return await automatic_pipeline.status()


@app.get("/api/pipeline/sources/{source}/records")
async def get_pipeline_source_records(
    source: Literal["wearable", "uav", "environment", "gis_segments"],
    limit: int = 200,
) -> dict:
    """Return a bounded record preview for a dedicated source module."""
    try:
        return await automatic_pipeline.records(source, limit)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="数据类型不存在") from error


@app.post("/api/pipeline/sources/{source}/reset")
async def reset_pipeline_source(
    source: Literal["wearable", "uav", "environment", "gis_segments"],
) -> dict:
    """Clear one source while retaining other imported datasets."""
    try:
        result = await automatic_pipeline.reset_source(source)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="数据类型不存在") from error
    return {"status": "ok", **result}


PIPELINE_CSV_TEMPLATES = {
    "wearable": (
        "timestamp,source_id,athlete_id,segment_id,distance_km,speed_m_s,heart_rate_bpm,spo2_pct,athlete_status,data_quality,data_status\n"
        "2026-10-13 09:30:00,WRIST-01,R001,S1,1.2,2.8,156,96,normal,0.95,模拟\n"
    ),
    "uav": (
        "timestamp,source_id,segment_id,person_count,observed_area_m2,avg_speed_m_s,suspected_fall_count,abnormal_motion_count,data_quality,data_status\n"
        "2026-10-13 09:30:00,UAV-01,S1,42,180,1.8,0,1,0.92,模拟\n"
    ),
    "environment": (
        "timestamp,source_id,segment_id,temperature_c,humidity_pct,wind_speed_m_s,rainfall_mm,data_quality,data_status\n"
        "2026-10-13 09:30:00,WEATHER-01,S1,27.6,68,2.1,0,0.98,模拟\n"
    ),
    "gis_segments": (
        "segment_id,start_km,end_km,road_width_m,mean_slope_pct,max_slope_pct,curve_level,emergency_access,nearest_medical_distance_km,data_status\n"
        "S1,0,5,8,1.5,3,中,方便,0.3,模拟\n"
    ),
}


@app.get("/api/pipeline/templates/{source}.csv")
async def download_pipeline_template(
    source: Literal["wearable", "uav", "environment", "gis_segments"],
) -> Response:
    """Download a UTF-8 CSV template for one managed source."""
    content = "\ufeff" + PIPELINE_CSV_TEMPLATES[source]
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{source}-template.csv"'},
    )


@app.post("/api/pipeline/reset")
async def reset_pipeline() -> dict[str, str]:
    """清空V0.1内存数据，便于重新进行一轮原型实验。"""
    await automatic_pipeline.reset()
    return {"status": "ok", "message": "自动处理管道数据已清空"}


@app.get("/api/snapshot", response_model=PlatformSnapshot)
async def get_snapshot() -> PlatformSnapshot:
    return await simulation.snapshot()


@app.get("/api/analytics")
async def get_analytics() -> dict:
    """Full simulation alert history and bounded health trend samples."""
    return await simulation.analytics()


@app.get("/api/export")
async def export_results(mode: Literal["simulation", "pipeline"] = "simulation") -> Response:
    state = await simulation.export_state()
    pipeline = None
    if mode == "pipeline":
        pipeline = [result.model_dump(mode="json") for result in await automatic_pipeline.results()]
    contents = create_export_bundle(state, pipeline)
    filename = f"zhihui-run-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.zip"
    return Response(
        content=contents,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/technical-docs/{slug}")
async def technical_document(slug: str) -> FileResponse:
    filename = TECHNICAL_DOCS.get(slug)
    if filename is None or not (DOCS_DIR / filename).is_file():
        raise HTTPException(status_code=404, detail="技术文档不存在")
    return FileResponse(DOCS_DIR / filename, media_type="text/markdown; charset=utf-8", filename=filename)


@app.post("/api/simulation/events")
async def inject_event(request: SimulationEventRequest):
    return await simulation.inject_event(request.event_type, request.segment_id)


@app.post("/api/simulation/control", response_model=PlatformSnapshot)
async def control_simulation(request: SimulationControlRequest) -> PlatformSnapshot:
    return await simulation.control(request.action)


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    alert = await simulation.acknowledge_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="报警记录不存在")
    return alert


@app.post("/api/alerts/{alert_id}/action")
async def handle_alert(alert_id: str, request: AlertActionRequest):
    alert = await simulation.handle_alert_action(alert_id, request.action)
    if alert is None:
        raise HTTPException(status_code=404, detail="报警记录不存在")
    return alert


@app.websocket("/ws/live")
async def live_updates(websocket: WebSocket) -> None:
    await hub.connect(websocket)
    try:
        snapshot = await simulation.snapshot()
        await websocket.send_json(snapshot.model_dump(mode="json"))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(websocket)
