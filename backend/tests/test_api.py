from fastapi.testclient import TestClient

from backend.app.main import app


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
        assert payload["drones"]


def test_can_inject_fall_event() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/simulation/events",
            json={"event_type": "fall", "segment_id": "S4"},
        )
        assert response.status_code == 200
        assert response.json()["event_type"] == "fall"


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
