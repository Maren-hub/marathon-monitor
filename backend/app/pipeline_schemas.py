from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DataStatus = Literal["模拟", "公开", "实测"]
AthleteReadingStatus = Literal["normal", "warning", "fallen", "finished"]
MonitoringFocus = Literal["crowd", "health", "balanced"]


class WearableReading(BaseModel):
    timestamp: datetime
    source_id: str = Field(min_length=1)
    athlete_id: str = Field(min_length=1)
    segment_id: str = Field(pattern=r"^S\d+$")
    distance_km: float = Field(ge=0, le=100)
    speed_m_s: float = Field(ge=0, le=15)
    heart_rate_bpm: int = Field(ge=30, le=230)
    spo2_pct: float = Field(ge=70, le=100)
    athlete_status: AthleteReadingStatus = "normal"
    data_quality: float = Field(default=1.0, ge=0, le=1)
    data_status: DataStatus = "实测"


class UavReading(BaseModel):
    timestamp: datetime
    source_id: str = Field(min_length=1)
    segment_id: str = Field(pattern=r"^S\d+$")
    person_count: int = Field(ge=0)
    observed_area_m2: float = Field(gt=0)
    avg_speed_m_s: float = Field(ge=0, le=15)
    suspected_fall_count: int = Field(default=0, ge=0)
    abnormal_motion_count: int = Field(default=0, ge=0)
    data_quality: float = Field(default=1.0, ge=0, le=1)
    data_status: DataStatus = "实测"


class EnvironmentReading(BaseModel):
    timestamp: datetime
    source_id: str = Field(min_length=1)
    segment_id: str = Field(pattern=r"^S\d+$")
    temperature_c: float = Field(ge=-30, le=60)
    humidity_pct: float = Field(ge=0, le=100)
    wind_speed_m_s: float = Field(ge=0, le=80)
    rainfall_mm: float = Field(default=0, ge=0)
    data_quality: float = Field(default=1.0, ge=0, le=1)
    data_status: DataStatus = "实测"


class GisSegmentReading(BaseModel):
    segment_id: str = Field(pattern=r"^S\d+$")
    start_km: float = Field(ge=0)
    end_km: float = Field(gt=0)
    road_width_m: float = Field(gt=0, le=100)
    mean_slope_pct: float = Field(ge=0, le=100)
    max_slope_pct: float = Field(ge=0, le=100)
    curve_level: Literal["低", "中", "高"]
    emergency_access: Literal["方便", "一般", "困难"]
    nearest_medical_distance_km: float = Field(ge=0)
    data_status: DataStatus = "实测"


class PipelineIngestRequest(BaseModel):
    wearable: list[WearableReading] = Field(default_factory=list)
    uav: list[UavReading] = Field(default_factory=list)
    environment: list[EnvironmentReading] = Field(default_factory=list)
    gis_segments: list[GisSegmentReading] = Field(default_factory=list)


class FeatureSignals(BaseModel):
    density_signal: float = Field(ge=0, le=1)
    slowdown_signal: float = Field(ge=0, le=1)
    high_hr_signal: float = Field(ge=0, le=1)
    low_spo2_signal: float = Field(ge=0, le=1)
    warning_ratio: float = Field(ge=0, le=1)
    road_constraint_signal: float = Field(ge=0, le=1)
    heat_humidity_signal: float = Field(ge=0, le=1)


class SegmentFusionResult(BaseModel):
    window_start: datetime
    window_seconds: int
    segment_id: str
    record_status: Literal["usable", "partial"]
    missing_sources: list[str]
    source_presence: dict[str, bool]
    data_confidence: float = Field(ge=0, le=1)

    sample_athlete_count: int = 0
    avg_athlete_speed_m_s: float | None = None
    avg_heart_rate_bpm: float | None = None
    max_heart_rate_bpm: int | None = None
    min_spo2_pct: float | None = None
    warning_count: int = 0

    uav_person_count: int | None = None
    crowd_density_p_m2: float | None = None
    uav_avg_speed_m_s: float | None = None
    suspected_fall_count: int = 0
    abnormal_motion_count: int = 0

    road_width_m: float | None = None
    mean_slope_pct: float | None = None
    curve_level: str | None = None
    emergency_access: str | None = None
    nearest_medical_distance_km: float | None = None

    temperature_c: float | None = None
    humidity_pct: float | None = None
    wind_speed_m_s: float | None = None

    features: FeatureSignals | None = None
    crowd_risk: float | None = Field(default=None, ge=0, le=1)
    health_risk: float | None = Field(default=None, ge=0, le=1)
    dominant_risk: float | None = Field(default=None, ge=0, le=1)
    risk_level: Literal["low", "medium", "high"] | None = None
    focus: MonitoringFocus | None = None
    focus_label: str | None = None
    monitoring_tasks: list[str] = Field(default_factory=list)
    recommended_units: list[str] = Field(default_factory=list)
    rule_version: str = "prototype-v0.1"


class PipelineIngestResponse(BaseModel):
    accepted: dict[str, int]
    stored: dict[str, int]
    results: list[SegmentFusionResult]

