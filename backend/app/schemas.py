from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RiskFocus = Literal["crowd", "health", "balanced"]
AlertLevel = Literal["info", "warning", "critical"]
AthleteStatus = Literal["normal", "warning", "fallen", "finished"]


class RaceSummary(BaseModel):
    name: str = "2026校园智慧路跑模拟赛"
    status: Literal["running", "paused"] = "running"
    elapsed_seconds: int = 0
    simulation_speed: int = 30
    total_distance_km: float = 42.195
    temperature_c: float = 27.6
    humidity_percent: float = 68.0


class SegmentState(BaseModel):
    id: str
    name: str
    start_km: float
    end_km: float
    coordinates: list[list[float]]
    athlete_count: int = 0
    crowd_risk: float = Field(ge=0, le=1)
    health_risk: float = Field(ge=0, le=1)
    focus: RiskFocus
    focus_label: str
    monitoring_tasks: list[str]


class AthleteState(BaseModel):
    id: str
    bib: str
    longitude: float
    latitude: float
    distance_km: float
    pace_min_km: float
    heart_rate: int
    status: AthleteStatus
    segment_id: str


class DroneState(BaseModel):
    id: str
    name: str
    longitude: float
    latitude: float
    altitude_m: float
    battery_percent: float
    task: str
    target_segment_id: str


class AlertState(BaseModel):
    id: str
    created_at: datetime
    level: AlertLevel
    event_type: Literal["crowd", "fall", "vital", "system"]
    title: str
    message: str
    segment_id: str
    athlete_id: str | None = None
    status: Literal["new", "acknowledged", "resolved"] = "new"


class PlatformStats(BaseModel):
    online_athletes: int
    active_drones: int
    open_alerts: int
    high_risk_segments: int


class DemoTimelineState(BaseModel):
    enabled: bool = False
    elapsed_seconds: int = 0
    duration_seconds: int = 0
    progress_percent: float = Field(ge=0, le=100)
    current_title: str = "等待自动演示"
    current_segment_id: str | None = None
    next_event_title: str | None = None
    next_event_segment_id: str | None = None
    next_event_in_seconds: int | None = None
    completed: bool = False


class PlatformSnapshot(BaseModel):
    generated_at: datetime
    race: RaceSummary
    segments: list[SegmentState]
    athletes: list[AthleteState]
    drones: list[DroneState]
    alerts: list[AlertState]
    stats: PlatformStats
    demo: DemoTimelineState


class SimulationEventRequest(BaseModel):
    event_type: Literal["crowd", "fall", "vital"]
    segment_id: str | None = None


class SimulationControlRequest(BaseModel):
    action: Literal["start", "pause", "reset", "auto_start"]
