import json
import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook

import backend.app.campus_route as campus_route
from backend.app.main import app


SAMPLE_PIPELINE_FILE = Path(__file__).parents[2] / "data" / "pipeline_sample.json"


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_snapshot_contains_platform_modules() -> None:
    with TestClient(app) as client:
        response = client.get("/api/snapshot")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["segments"]) == 5
        assert payload["race"]["name"] == "2026校园智慧路跑模拟赛"
        assert len(payload["athletes"]) == 120
        assert 70 <= payload["athletes"][0]["blood_oxygen"] <= 100
        assert 0 <= payload["athletes"][0]["fatigue_percent"] <= 100
        assert payload["athletes"][0]["group"] in {"竞速组", "大众组", "体验组"}
        assert payload["drones"][0]["status"] in {"patrol", "dispatch"}
        assert payload["drones"][0]["camera_mode"]
        assert payload["drones"]
        assert len(payload["review"]["segments"]) == 5


def test_can_inject_fall_event() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/simulation/events",
            json={"event_type": "fall", "segment_id": "S4"},
        )
        assert response.status_code == 200
        assert response.json()["event_type"] == "fall"


def test_alert_can_complete_response_workflow() -> None:
    with TestClient(app) as client:
        event = client.post(
            "/api/simulation/events",
            json={"event_type": "fall", "segment_id": "S3"},
        ).json()
        dispatch = client.post(
            f"/api/alerts/{event['id']}/action",
            json={"action": "medical_dispatch"},
        )
        assert dispatch.status_code == 200
        assert dispatch.json()["status"] == "acknowledged"
        assert dispatch.json()["assigned_unit"] == "医疗救援组 M-02"
        resolved = client.post(
            f"/api/alerts/{event['id']}/action",
            json={"action": "resolve"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "resolved"
        assert resolved.json()["resolution_seconds"] is not None
        review = client.get("/api/snapshot").json()["review"]
        assert review["total_events"] >= 1
        assert review["resolved_events"] >= 1
        assert review["drone_dispatches"] >= 1


def test_reset_pauses_race_with_all_athletes_ready() -> None:
    with TestClient(app) as client:
        response = client.post("/api/simulation/control", json={"action": "reset"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["race"]["status"] == "paused"
        assert payload["stats"]["online_athletes"] == 120


def test_auto_demo_starts_from_timeline() -> None:
    with TestClient(app) as client:
        response = client.post("/api/simulation/control", json={"action": "auto_start"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["demo"]["enabled"] is True
        assert payload["demo"]["current_title"] == "赛事开始"
        assert payload["demo"]["next_event_title"] == "起跑后局部拥挤"
        assert payload["demo"]["next_event_in_seconds"] == 40


def test_pipeline_automatically_fuses_scores_and_assigns_tasks() -> None:
    payload = json.loads(SAMPLE_PIPELINE_FILE.read_text(encoding="utf-8"))
    with TestClient(app) as client:
        client.post("/api/pipeline/reset")
        response = client.post("/api/pipeline/ingest", json=payload)
        assert response.status_code == 200
        results = {item["segment_id"]: item for item in response.json()["results"]}

        assert results["S1"]["record_status"] == "usable"
        assert results["S1"]["focus"] == "crowd"
        assert results["S1"]["crowd_risk"] > results["S1"]["health_risk"]
        assert "安保疏导组" in results["S1"]["recommended_units"]

        assert results["S4"]["record_status"] == "usable"
        assert results["S4"]["focus"] == "health"
        assert results["S4"]["health_risk"] > results["S4"]["crowd_risk"]
        assert "医疗救援组" in results["S4"]["recommended_units"]


def test_pipeline_status_summarises_sources_without_raw_records() -> None:
    payload = json.loads(SAMPLE_PIPELINE_FILE.read_text(encoding="utf-8"))
    with TestClient(app) as client:
        client.post("/api/pipeline/reset")
        assert client.post("/api/pipeline/ingest", json=payload).status_code == 200
        response = client.get("/api/pipeline/status")
        assert response.status_code == 200
        status = response.json()
        assert status["stored"]["wearable"] == len(payload["wearable"])
        assert status["stored"]["uav"] == len(payload["uav"])
        assert status["usable_results"] == 2
        assert status["partial_results"] == 0
        assert status["source_states"]["environment"]["available"] is True
        assert status["storage_mode"] == "memory"
        assert "records" not in status


def test_pipeline_rejects_impossible_sensor_value() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/pipeline/ingest",
            json={
                "wearable": [
                    {
                        "timestamp": "2026-08-25T09:32:00",
                        "source_id": "WB-R001",
                        "athlete_id": "R001",
                        "segment_id": "S1",
                        "distance_km": 3.5,
                        "speed_m_s": 2.8,
                        "heart_rate_bpm": 150,
                        "spo2_pct": 900,
                    }
                ]
            },
        )
        assert response.status_code == 422


def test_analytics_tracks_events_and_resets() -> None:
    with TestClient(app) as client:
        client.post("/api/simulation/control", json={"action": "reset"})
        initial = client.get("/api/analytics").json()
        assert initial["source"] == "simulation"
        assert len(initial["health_history"]) == 1
        assert initial["alerts"] == []
        client.post("/api/simulation/events", json={"event_type": "crowd", "segment_id": "S2"})
        current = client.get("/api/analytics").json()
        assert current["alerts"][0]["segment_id"] == "S2"
        assert len(current["health_history"]) == 2
        client.post("/api/simulation/control", json={"action": "reset"})
        assert client.get("/api/analytics").json()["alerts"] == []


def test_export_contains_full_history_and_source_labels() -> None:
    with TestClient(app) as client:
        client.post("/api/simulation/control", json={"action": "reset"})
        client.post("/api/simulation/events", json={"event_type": "fall", "segment_id": "S4"})
        response = client.get("/api/export")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert {"snapshot.json", "segments.csv", "alerts.csv", "report.html", "manifest.json"} <= set(archive.namelist())
            alerts = json.loads(archive.read("alerts.json"))
            assert any(item["event_type"] == "fall" for item in alerts)
            segments = json.loads(archive.read("segments.json"))
            assert all(item["data_source"] == "simulation" for item in segments)
            assert b"<!doctype html>" in archive.read("report.html")


def test_technical_documents_are_whitelisted() -> None:
    with TestClient(app) as client:
        assert client.get("/api/technical-docs/architecture").status_code == 200
        assert client.get("/api/technical-docs/unknown").status_code == 404


def test_pipeline_export_marks_fallback_segments() -> None:
    payload = json.loads(SAMPLE_PIPELINE_FILE.read_text(encoding="utf-8"))
    with TestClient(app) as client:
        client.post("/api/pipeline/reset")
        assert client.post("/api/pipeline/ingest", json=payload).status_code == 200
        response = client.get("/api/export?mode=pipeline")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            segments = {item["id"]: item for item in json.loads(archive.read("segments.json"))}
            assert segments["S1"]["data_source"] == "pipeline"
            assert segments["S4"]["data_source"] == "pipeline"
            assert segments["S2"]["data_source"] == "simulation-fallback"


def test_csv_drag_import_shows_partial_source() -> None:
    csv_data = "采集时间,设备编号,赛段编号,人数,观测面积,平均速度\n2026-10-10 09:30:00,UAV-01,S1,35,120,1.7\n"
    with TestClient(app) as client:
        client.post("/api/pipeline/reset")
        response = client.post(
            "/api/pipeline/import-file?filename=drone.csv&default_status=%E6%A8%A1%E6%8B%9F",
            content=csv_data.encode("utf-8-sig"),
            headers={"content-type": "application/octet-stream"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"]["uav"] == 1
        assert payload["usable_segments"] == []
        assert payload["partial_segments"][0]["segment_id"] == "S1"
        assert "wearable" in payload["partial_segments"][0]["missing_sources"]


def test_xlsx_drag_import_runs_full_pipeline() -> None:
    sample = json.loads(SAMPLE_PIPELINE_FILE.read_text(encoding="utf-8"))
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, records in sample.items():
        sheet = workbook.create_sheet(name)
        fields = list(records[0])
        sheet.append(fields)
        for record in records:
            sheet.append([record.get(field) for field in fields])
    output = io.BytesIO()
    workbook.save(output)
    with TestClient(app) as client:
        client.post("/api/pipeline/reset")
        response = client.post(
            "/api/pipeline/import-file?filename=sample.xlsx&default_status=%E6%A8%A1%E6%8B%9F",
            content=output.getvalue(),
            headers={"content-type": "application/octet-stream"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["usable_segments"] == ["S1", "S4"]
        assert payload["accepted"]["wearable"] == len(sample["wearable"])
        assert len(payload["sheets"]) == 4


def test_invalid_sheet_does_not_partially_import() -> None:
    csv_data = (
        "采集时间,设备编号,赛段编号,人数,观测面积,平均速度\n"
        "2026-10-10 09:30:00,UAV-01,S1,35,120,1.7\n"
        "2026-10-10 09:30:01,UAV-02,S1,10,0,1.2\n"
    )
    with TestClient(app) as client:
        client.post("/api/pipeline/reset")
        response = client.post(
            "/api/pipeline/import-file?filename=bad.csv",
            content=csv_data.encode("utf-8"),
            headers={"content-type": "application/octet-stream"},
        )
        assert response.status_code == 422
        assert "第3行" in response.text
        assert client.get("/api/pipeline/segments").json() == []


def test_dedicated_source_management_preview_and_clear() -> None:
    csv_data = "采集时间,设备编号,赛段编号,人数,观测面积,平均速度\n2026-10-13 09:30:00,UAV-01,S1,35,120,1.7\n"
    with TestClient(app) as client:
        client.post("/api/pipeline/reset")
        imported = client.post(
            "/api/pipeline/import-file?filename=uav.csv&expected_kind=uav",
            content=csv_data.encode("utf-8-sig"),
            headers={"content-type": "application/octet-stream"},
        )
        assert imported.status_code == 200, imported.text
        preview = client.get("/api/pipeline/sources/uav/records").json()
        assert preview["total"] == 1
        assert preview["records"][0]["source_id"] == "UAV-01"
        cleared = client.post("/api/pipeline/sources/uav/reset").json()
        assert cleared["removed"] == 1
        assert client.get("/api/pipeline/sources/uav/records").json()["records"] == []


def test_dedicated_source_import_rejects_wrong_dataset() -> None:
    csv_data = "采集时间,设备编号,赛段编号,人数,观测面积,平均速度\n2026-10-13 09:30:00,UAV-01,S1,35,120,1.7\n"
    with TestClient(app) as client:
        response = client.post(
            "/api/pipeline/import-file?filename=uav.csv&expected_kind=wearable",
            content=csv_data.encode("utf-8-sig"),
            headers={"content-type": "application/octet-stream"},
        )
        assert response.status_code == 422
        assert "只接收手环体征数据" in response.text


def test_source_csv_template_download() -> None:
    with TestClient(app) as client:
        response = client.get("/api/pipeline/templates/wearable.csv")
        assert response.status_code == 200
        assert "athlete_id" in response.text
        assert response.headers["content-type"].startswith("text/csv")


def test_import_rejects_direct_identifiers() -> None:
    csv_data = (
        "采集时间,设备编号,赛段编号,人数,观测面积,平均速度,姓名\n"
        "2026-10-10 09:30:00,UAV-01,S1,35,120,1.7,张三\n"
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/pipeline/import-file?filename=private.csv",
            content=csv_data.encode("utf-8"),
            headers={"content-type": "application/octet-stream"},
        )
        assert response.status_code == 422
        assert "脱敏" in response.text


def test_campus_geojson_import_persists_route_and_sites(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(campus_route, "ROUTE_FILE", tmp_path / "campus_route_import.json")
    route = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"segment_id": "C1", "name": "同伴绘制路线"},
            "geometry": {"type": "LineString", "coordinates": [[118.813, 32.083], [118.814, 32.083]]},
        }],
    }
    sites = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"kind": "medical", "name": "候选医疗点"},
            "geometry": {"type": "Point", "coordinates": [118.8135, 32.083]},
        }],
    }
    with TestClient(app) as client:
        assert client.get("/api/campus-route").json()["segments"] == []
        imported = client.post(
            "/api/campus-route/import?kind=route&filename=course.geojson",
            content=json.dumps(route).encode("utf-8"),
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["route_length_km"] > 0
        assert len(imported.json()["segments"]) == 1
        points = client.post(
            "/api/campus-route/import?kind=sites&filename=sites.geojson",
            content=json.dumps(sites).encode("utf-8"),
        )
        assert points.status_code == 200, points.text
        assert points.json()["sites"][0]["kind"] == "medical"
        assert len(client.get("/api/campus-route").json()["segments"]) == 1


def test_campus_route_rejects_wrong_coordinates_without_replacing_saved_data(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(campus_route, "ROUTE_FILE", tmp_path / "campus_route_import.json")
    valid = {"type": "Feature", "properties": {}, "geometry": {
        "type": "LineString", "coordinates": [[118.813, 32.083], [118.814, 32.083]]}}
    projected = {"type": "Feature", "properties": {}, "geometry": {
        "type": "LineString", "coordinates": [[500000, 3500000], [500100, 3500000]]}}
    with TestClient(app) as client:
        assert client.post(
            "/api/campus-route/import?kind=route&filename=good.geojson",
            content=json.dumps(valid).encode("utf-8"),
        ).status_code == 200
        bad = client.post(
            "/api/campus-route/import?kind=route&filename=wrong.geojson",
            content=json.dumps(projected).encode("utf-8"),
        )
        assert bad.status_code == 422
        assert client.get("/api/campus-route").json()["route_filename"] == "good.geojson"
