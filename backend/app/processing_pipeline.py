from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from statistics import fmean

from .pipeline_schemas import (
    EnvironmentReading,
    FeatureSignals,
    GisSegmentReading,
    PipelineIngestRequest,
    PipelineIngestResponse,
    SegmentFusionResult,
    UavReading,
    WearableReading,
)


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def rounded(value: float) -> float:
    return round(clamp(value), 3)


class AutomaticDataPipeline:
    """统一接收模拟或实测数据，并产生赛段级风险与任务建议。

    V0.1 使用内存存储和原型规则。输入端可以替换为 Excel、设备 API、
    MQTT 或数据库适配器，而后续融合与风险计算接口保持不变。
    """

    RULE_VERSION = "prototype-v0.1"

    def __init__(self, window_seconds: int = 60) -> None:
        self.window_seconds = window_seconds
        self._lock = asyncio.Lock()
        self._wearable: dict[tuple, WearableReading] = {}
        self._uav: dict[tuple, UavReading] = {}
        self._environment: dict[tuple, EnvironmentReading] = {}
        self._gis: dict[str, GisSegmentReading] = {}

    def _window_start(self, timestamp: datetime) -> datetime:
        seconds = int(timestamp.timestamp())
        floored = seconds - seconds % self.window_seconds
        if timestamp.tzinfo is None:
            return datetime.fromtimestamp(floored)
        return datetime.fromtimestamp(floored, tz=timestamp.tzinfo)

    async def reset(self) -> None:
        async with self._lock:
            self._wearable.clear()
            self._uav.clear()
            self._environment.clear()
            self._gis.clear()

    async def ingest(self, request: PipelineIngestRequest) -> PipelineIngestResponse:
        async with self._lock:
            for item in request.wearable:
                key = (item.timestamp, item.source_id, item.athlete_id)
                self._wearable[key] = item
            for item in request.uav:
                key = (item.timestamp, item.source_id, item.segment_id)
                self._uav[key] = item
            for item in request.environment:
                key = (item.timestamp, item.source_id, item.segment_id)
                self._environment[key] = item
            for item in request.gis_segments:
                self._gis[item.segment_id] = item

            results = self._build_results_unlocked()
            return PipelineIngestResponse(
                accepted={
                    "wearable": len(request.wearable),
                    "uav": len(request.uav),
                    "environment": len(request.environment),
                    "gis_segments": len(request.gis_segments),
                },
                stored=self._stored_counts(),
                results=results,
            )

    async def results(self) -> list[SegmentFusionResult]:
        async with self._lock:
            return self._build_results_unlocked()

    def rules(self) -> dict:
        return {
            "version": self.RULE_VERSION,
            "status": "原型规则，尚未经过赛事或医学验证",
            "time_window_seconds": self.window_seconds,
            "feature_references": {
                "density_p_m2_upper": 0.5,
                "normal_speed_m_s": 3.0,
                "strong_slowdown_speed_m_s": 1.5,
                "heart_rate_signal_range_bpm": [160, 200],
                "spo2_signal_range_pct": [96, 88],
                "road_width_signal_range_m": [10, 6],
                "mean_slope_signal_upper_pct": 5,
                "temperature_signal_range_c": [28, 35],
                "humidity_signal_range_pct": [60, 90],
            },
            "risk_weights": {
                "crowd": {
                    "density_signal": 0.50,
                    "slowdown_signal": 0.30,
                    "road_constraint_signal": 0.20,
                },
                "health": {
                    "high_hr_signal": 0.24,
                    "low_spo2_signal": 0.24,
                    "warning_ratio": 0.18,
                    "slowdown_signal": 0.12,
                    "heat_humidity_signal": 0.12,
                    "road_constraint_signal": 0.10,
                },
            },
            "focus_difference_threshold": 0.12,
        }

    def _stored_counts(self) -> dict[str, int]:
        return {
            "wearable": len(self._wearable),
            "uav": len(self._uav),
            "environment": len(self._environment),
            "gis_segments": len(self._gis),
        }

    def _latest_per_athlete(
        self, readings: list[WearableReading]
    ) -> list[WearableReading]:
        latest: dict[str, WearableReading] = {}
        for reading in readings:
            current = latest.get(reading.athlete_id)
            if current is None or reading.timestamp > current.timestamp:
                latest[reading.athlete_id] = reading
        return list(latest.values())

    @staticmethod
    def _best_quality(readings: list):
        if not readings:
            return None
        return max(readings, key=lambda item: (item.data_quality, item.timestamp))

    def _build_results_unlocked(self) -> list[SegmentFusionResult]:
        wearable_groups: dict[tuple[datetime, str], list[WearableReading]] = defaultdict(list)
        uav_groups: dict[tuple[datetime, str], list[UavReading]] = defaultdict(list)
        environment_groups: dict[tuple[datetime, str], list[EnvironmentReading]] = defaultdict(list)

        for item in self._wearable.values():
            wearable_groups[(self._window_start(item.timestamp), item.segment_id)].append(item)
        for item in self._uav.values():
            uav_groups[(self._window_start(item.timestamp), item.segment_id)].append(item)
        for item in self._environment.values():
            environment_groups[(self._window_start(item.timestamp), item.segment_id)].append(item)

        keys = set(wearable_groups) | set(uav_groups) | set(environment_groups)
        results: list[SegmentFusionResult] = []
        for window_start, segment_id in sorted(keys, key=lambda key: (key[0], key[1])):
            athletes = self._latest_per_athlete(wearable_groups.get((window_start, segment_id), []))
            uav = self._best_quality(uav_groups.get((window_start, segment_id), []))
            environment = self._best_quality(environment_groups.get((window_start, segment_id), []))
            gis = self._gis.get(segment_id)
            results.append(self._fuse(window_start, segment_id, athletes, uav, environment, gis))
        return results

    def _fuse(
        self,
        window_start: datetime,
        segment_id: str,
        athletes: list[WearableReading],
        uav: UavReading | None,
        environment: EnvironmentReading | None,
        gis: GisSegmentReading | None,
    ) -> SegmentFusionResult:
        presence = {
            "wearable": bool(athletes),
            "uav": uav is not None,
            "environment": environment is not None,
            "gis": gis is not None,
        }
        missing_sources = [name for name, present in presence.items() if not present]
        record_status = "usable" if not missing_sources else "partial"

        qualities: list[float] = [item.data_quality for item in athletes]
        if uav is not None:
            qualities.append(uav.data_quality)
        if environment is not None:
            qualities.append(environment.data_quality)
        completeness = sum(presence.values()) / len(presence)
        mean_quality = fmean(qualities) if qualities else 0.0
        data_confidence = round(mean_quality * completeness, 3)

        avg_speed = round(fmean(item.speed_m_s for item in athletes), 3) if athletes else None
        avg_hr = round(fmean(item.heart_rate_bpm for item in athletes), 2) if athletes else None
        max_hr = max((item.heart_rate_bpm for item in athletes), default=None)
        min_spo2 = min((item.spo2_pct for item in athletes), default=None)
        warning_count = sum(item.athlete_status in {"warning", "fallen"} for item in athletes)

        result = SegmentFusionResult(
            window_start=window_start,
            window_seconds=self.window_seconds,
            segment_id=segment_id,
            record_status=record_status,
            missing_sources=missing_sources,
            source_presence=presence,
            data_confidence=data_confidence,
            sample_athlete_count=len(athletes),
            avg_athlete_speed_m_s=avg_speed,
            avg_heart_rate_bpm=avg_hr,
            max_heart_rate_bpm=max_hr,
            min_spo2_pct=min_spo2,
            warning_count=warning_count,
            uav_person_count=uav.person_count if uav else None,
            crowd_density_p_m2=(
                round(uav.person_count / uav.observed_area_m2, 3) if uav else None
            ),
            uav_avg_speed_m_s=uav.avg_speed_m_s if uav else None,
            suspected_fall_count=uav.suspected_fall_count if uav else 0,
            abnormal_motion_count=uav.abnormal_motion_count if uav else 0,
            road_width_m=gis.road_width_m if gis else None,
            mean_slope_pct=gis.mean_slope_pct if gis else None,
            curve_level=gis.curve_level if gis else None,
            emergency_access=gis.emergency_access if gis else None,
            nearest_medical_distance_km=gis.nearest_medical_distance_km if gis else None,
            temperature_c=environment.temperature_c if environment else None,
            humidity_pct=environment.humidity_pct if environment else None,
            wind_speed_m_s=environment.wind_speed_m_s if environment else None,
            rule_version=self.RULE_VERSION,
        )

        if record_status == "usable":
            self._add_features_risk_and_tasks(result)
        return result

    def _add_features_risk_and_tasks(self, result: SegmentFusionResult) -> None:
        assert result.crowd_density_p_m2 is not None
        assert result.uav_avg_speed_m_s is not None
        assert result.max_heart_rate_bpm is not None
        assert result.min_spo2_pct is not None
        assert result.road_width_m is not None
        assert result.mean_slope_pct is not None
        assert result.temperature_c is not None
        assert result.humidity_pct is not None

        density = clamp(result.crowd_density_p_m2 / 0.5)
        slowdown = clamp((3.0 - result.uav_avg_speed_m_s) / 1.5)
        high_hr = clamp((result.max_heart_rate_bpm - 160) / 40)
        low_spo2 = clamp((96 - result.min_spo2_pct) / 8)
        warning_ratio = clamp(result.warning_count / max(result.sample_athlete_count, 1))
        road_constraint = (
            clamp((10 - result.road_width_m) / 4) + clamp(result.mean_slope_pct / 5)
        ) / 2
        heat_humidity = (
            clamp((result.temperature_c - 28) / 7)
            + clamp((result.humidity_pct - 60) / 30)
        ) / 2

        result.features = FeatureSignals(
            density_signal=rounded(density),
            slowdown_signal=rounded(slowdown),
            high_hr_signal=rounded(high_hr),
            low_spo2_signal=rounded(low_spo2),
            warning_ratio=rounded(warning_ratio),
            road_constraint_signal=rounded(road_constraint),
            heat_humidity_signal=rounded(heat_humidity),
        )

        crowd_risk = (
            density * 0.50
            + slowdown * 0.30
            + road_constraint * 0.20
        )
        health_risk = (
            high_hr * 0.24
            + low_spo2 * 0.24
            + warning_ratio * 0.18
            + slowdown * 0.12
            + heat_humidity * 0.12
            + road_constraint * 0.10
        )
        if result.suspected_fall_count:
            health_risk += 0.25
        elif result.abnormal_motion_count:
            health_risk += 0.10

        result.crowd_risk = rounded(crowd_risk)
        result.health_risk = rounded(health_risk)
        result.dominant_risk = max(result.crowd_risk, result.health_risk)
        result.risk_level = (
            "high" if result.dominant_risk >= 0.65 else "medium" if result.dominant_risk >= 0.35 else "low"
        )

        difference = result.crowd_risk - result.health_risk
        if difference > 0.12:
            result.focus = "crowd"
            result.focus_label = "聚集安全优先"
            result.monitoring_tasks = ["人群密度", "拥堵趋势", "越界识别"]
            result.recommended_units = ["UAV广角巡检", "安保疏导组"]
        elif difference < -0.12:
            result.focus = "health"
            result.focus_label = "个体安全优先"
            result.monitoring_tasks = ["跌倒识别", "异常步态", "体征复核"]
            result.recommended_units = ["UAV近距复核", "医疗救援组"]
        else:
            result.focus = "balanced"
            result.focus_label = "综合监测"
            result.monitoring_tasks = ["人群密度", "跌倒识别", "手环异常"]
            result.recommended_units = ["UAV常规巡检", "赛事指挥中心"]


automatic_pipeline = AutomaticDataPipeline()
