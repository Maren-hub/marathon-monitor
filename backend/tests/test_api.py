import json
from pathlib import Path

from fastapi.testclient import TestClient

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
