from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .schemas import AlertActionRequest, PlatformSnapshot, SimulationControlRequest, SimulationEventRequest
from .simulation import MarathonSimulation


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


@app.get("/api/snapshot", response_model=PlatformSnapshot)
async def get_snapshot() -> PlatformSnapshot:
    return await simulation.snapshot()


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
