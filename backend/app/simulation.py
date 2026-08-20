from __future__ import annotations

import asyncio
import json
import math
import random
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path

from .schemas import (
    AlertState,
    AthleteState,
    DroneState,
    PlatformSnapshot,
    PlatformStats,
    RaceSummary,
    SegmentState,
)


PublishCallback = Callable[[dict], Awaitable[None]]
SCENARIO_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_scenario.json"


SEGMENT_DEFINITIONS = [
    {
        "id": "S1",
        "name": "起跑疏散区",
        "start_km": 0.0,
        "end_km": 5.0,
        "coordinates": [
            [114.3510, 30.5350],
            [114.3560, 30.5380],
            [114.3620, 30.5405],
            [114.3690, 30.5410],
        ],
        "base_crowd": 0.78,
        "base_health": 0.16,
    },
    {
        "id": "S2",
        "name": "前程密集区",
        "start_km": 5.0,
        "end_km": 15.0,
        "coordinates": [
            [114.3690, 30.5410],
            [114.3750, 30.5390],
            [114.3810, 30.5350],
            [114.3840, 30.5290],
        ],
        "base_crowd": 0.70,
        "base_health": 0.24,
    },
    {
        "id": "S3",
        "name": "中程平衡区",
        "start_km": 15.0,
        "end_km": 28.0,
        "coordinates": [
            [114.3840, 30.5290],
            [114.3810, 30.5220],
            [114.3740, 30.5180],
            [114.3660, 30.5165],
        ],
        "base_crowd": 0.43,
        "base_health": 0.42,
    },
    {
        "id": "S4",
        "name": "后程体能风险区",
        "start_km": 28.0,
        "end_km": 37.0,
        "coordinates": [
            [114.3660, 30.5165],
            [114.3580, 30.5180],
            [114.3510, 30.5220],
            [114.3470, 30.5270],
        ],
        "base_crowd": 0.24,
        "base_health": 0.72,
    },
    {
        "id": "S5",
        "name": "终点综合保障区",
        "start_km": 37.0,
        "end_km": 42.195,
        "coordinates": [
            [114.3470, 30.5270],
            [114.3460, 30.5320],
            [114.3480, 30.5350],
            [114.3510, 30.5350],
        ],
        "base_crowd": 0.57,
        "base_health": 0.82,
    },
]


def load_demo_scenario() -> dict:
    """Load the synthetic race configuration used by the prototype."""
    with SCENARIO_PATH.open("r", encoding="utf-8") as scenario_file:
        return json.load(scenario_file)


def build_segment_definitions(scenario: dict) -> list[dict]:
    """Merge editable scenario values with the prototype route geometry."""
    configured_by_id = {item["id"]: item for item in scenario.get("segments", [])}
    definitions: list[dict] = []
    for default in SEGMENT_DEFINITIONS:
        configured = configured_by_id.get(default["id"], {})
        definitions.append(
            {
                **default,
                "name": configured.get("name", default["name"]),
                "start_km": float(configured.get("start_km", default["start_km"])),
                "end_km": float(configured.get("end_km", default["end_km"])),
                "base_crowd": float(configured.get("base_crowd_risk", default["base_crowd"])),
                "base_health": float(configured.get("base_health_risk", default["base_health"])),
            }
        )
    return definitions


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def interpolate_polyline(points: list[list[float]], progress: float) -> tuple[float, float]:
    progress = clamp(progress)
    scaled = progress * (len(points) - 1)
    index = min(int(scaled), len(points) - 2)
    local = scaled - index
    start, end = points[index], points[index + 1]
    longitude = start[0] + (end[0] - start[0]) * local
    latitude = start[1] + (end[1] - start[1]) * local
    return longitude, latitude


class MarathonSimulation:
    """An in-memory digital-twin simulator used until real devices are connected."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._random = random.Random(20260819)
        self.scenario: dict = {}
        self.segment_definitions: list[dict] = []
        self._tick = 0
        self._event_counter = 0
        self._running = True
        self._risk_boosts: dict[str, dict[str, float | int]] = {}
        self.race = RaceSummary()
        self.segments: list[SegmentState] = []
        self.athletes: list[AthleteState] = []
        self.drones: list[DroneState] = []
        self.alerts: list[AlertState] = []
        self._reset_state()

    def _reset_state(self) -> None:
        self.scenario = load_demo_scenario()
        self.segment_definitions = build_segment_definitions(self.scenario)
        self._random.seed(20260819)
        self._tick = 0
        self._event_counter = 0
        self._risk_boosts.clear()
        self._running = True
        race_config = self.scenario.get("race", {})
        weather = race_config.get("weather", {})
        self.race = RaceSummary(
            name=race_config.get("name", "校园马拉松模拟赛"),
            status="running",
            simulation_speed=int(race_config.get("simulation_speed", 30)),
            total_distance_km=float(race_config.get("total_distance_km", 42.195)),
            temperature_c=float(weather.get("temperature_c", 27.6)),
            humidity_percent=float(weather.get("humidity_percent", 68.0)),
        )
        self.segments = [
            SegmentState(
                id=item["id"],
                name=item["name"],
                start_km=item["start_km"],
                end_km=item["end_km"],
                coordinates=item["coordinates"],
                crowd_risk=item["base_crowd"],
                health_risk=item["base_health"],
                focus="balanced",
                focus_label="综合监测",
                monitoring_tasks=["人群密度", "异常步态"],
            )
            for item in self.segment_definitions
        ]
        self.athletes = []
        participant_config = self.scenario.get("participant_generation", {})
        participant_count = int(participant_config.get("count", 36))
        bib_start = int(participant_config.get("bib_start", 101))
        pace_range = participant_config.get("pace_min_km_range", [4.7, 7.2])
        for index in range(participant_count):
            spread_position = 3.6 * (1 - index / max(participant_count - 1, 1))
            distance = round(max(0.0, min(3.6, spread_position + self._random.uniform(-0.04, 0.04))), 3)
            segment = self._segment_for_distance(distance)
            longitude, latitude = self._location_for_distance(distance)
            pace = self._random.uniform(float(pace_range[0]), float(pace_range[1]))
            self.athletes.append(
                AthleteState(
                    id=f"A{index + 1:03d}",
                    bib=f"{bib_start + index:04d}",
                    longitude=longitude,
                    latitude=latitude,
                    distance_km=distance,
                    pace_min_km=pace,
                    heart_rate=self._random.randint(128, 158),
                    status="normal",
                    segment_id=segment.id,
                )
            )
        self.drones = [
            DroneState(
                id="UAV-01",
                name="巡检一号",
                longitude=114.3600,
                latitude=30.5400,
                altitude_m=85,
                battery_percent=96,
                task="起跑区人群密度巡检",
                target_segment_id="S1",
            ),
            DroneState(
                id="UAV-02",
                name="巡检二号",
                longitude=114.3500,
                latitude=30.5250,
                altitude_m=72,
                battery_percent=91,
                task="后程个体安全巡检",
                target_segment_id="S4",
            ),
        ]
        self.alerts = [
            AlertState(
                id="EVT-0001",
                created_at=datetime.now(timezone.utc),
                level="info",
                event_type="system",
                title="模拟系统已启动",
                message="当前使用模拟运动员、无人机和手环数据。",
                segment_id="S1",
                status="acknowledged",
            )
        ]
        self._recalculate_segments()

    def _segment_for_distance(self, distance_km: float) -> SegmentState:
        for segment in self.segments:
            if segment.start_km <= distance_km < segment.end_km:
                return segment
        return self.segments[-1]

    def _location_for_distance(self, distance_km: float) -> tuple[float, float]:
        segment_definition = self.segment_definitions[-1]
        for item in self.segment_definitions:
            if item["start_km"] <= distance_km < item["end_km"]:
                segment_definition = item
                break
        length = segment_definition["end_km"] - segment_definition["start_km"]
        progress = (distance_km - segment_definition["start_km"]) / length
        return interpolate_polyline(segment_definition["coordinates"], progress)

    def _recalculate_segments(self) -> None:
        counts = {segment.id: 0 for segment in self.segments}
        abnormal = {segment.id: 0 for segment in self.segments}
        for athlete in self.athletes:
            counts[athlete.segment_id] += 1
            if athlete.status in {"warning", "fallen"}:
                abnormal[athlete.segment_id] += 1

        max_count = max(max(counts.values()), 1)
        for index, segment in enumerate(self.segments):
            definition = self.segment_definitions[index]
            density_signal = counts[segment.id] / max_count
            wave = 0.04 * math.sin(self._tick / 6 + index)
            crowd_boost = 0.0
            health_boost = 0.0
            boost = self._risk_boosts.get(segment.id)
            if boost and int(boost["until"]) >= self._tick:
                crowd_boost = float(boost.get("crowd", 0.0))
                health_boost = float(boost.get("health", 0.0))

            progress_factor = segment.start_km / self.race.total_distance_km
            segment.athlete_count = counts[segment.id]
            segment.crowd_risk = round(
                clamp(definition["base_crowd"] * 0.58 + density_signal * 0.34 + wave + crowd_boost),
                3,
            )
            segment.health_risk = round(
                clamp(
                    definition["base_health"] * 0.72
                    + progress_factor * 0.16
                    + abnormal[segment.id] * 0.12
                    + max(0, wave / 2)
                    + health_boost
                ),
                3,
            )

            difference = segment.crowd_risk - segment.health_risk
            if difference > 0.12:
                segment.focus = "crowd"
                segment.focus_label = "聚集安全优先"
                segment.monitoring_tasks = ["人群密度", "拥堵趋势", "越界识别"]
            elif difference < -0.12:
                segment.focus = "health"
                segment.focus_label = "个体安全优先"
                segment.monitoring_tasks = ["跌倒识别", "异常步态", "体征复核"]
            else:
                segment.focus = "balanced"
                segment.focus_label = "综合监测"
                segment.monitoring_tasks = ["人群密度", "跌倒识别", "手环异常"]

    def _update_athletes(self) -> None:
        for athlete in self.athletes:
            if athlete.status == "fallen" or athlete.status == "finished":
                continue
            speed_kmh = 60 / athlete.pace_min_km
            fatigue = 1 - max(0, athlete.distance_km - 24) / 180
            athlete.distance_km = round(
                min(self.race.total_distance_km, athlete.distance_km + speed_kmh / 3600 * self.race.simulation_speed * fatigue),
                3,
            )
            if athlete.distance_km >= self.race.total_distance_km:
                athlete.status = "finished"
            segment = self._segment_for_distance(athlete.distance_km)
            athlete.segment_id = segment.id
            athlete.longitude, athlete.latitude = self._location_for_distance(athlete.distance_km)
            exertion = athlete.distance_km / self.race.total_distance_km
            noise = self._random.randint(-3, 3)
            athlete.heart_rate = int(clamp(132 + exertion * 45 + noise, 85, 205))
            if athlete.status == "warning" and self._tick % 20 == 0:
                athlete.status = "normal"

    def _update_drones(self) -> None:
        ranked_segments = sorted(
            self.segments,
            key=lambda item: max(item.crowd_risk, item.health_risk),
            reverse=True,
        )
        for index, drone in enumerate(self.drones):
            target = ranked_segments[index % len(ranked_segments)]
            midpoint = target.coordinates[len(target.coordinates) // 2]
            offset = 0.0007 * math.sin(self._tick / 5 + index * math.pi)
            drone.longitude = midpoint[0] + offset
            drone.latitude = midpoint[1] + offset / 2
            drone.altitude_m = round(78 + 10 * math.sin(self._tick / 9 + index), 1)
            drone.battery_percent = round(max(12, drone.battery_percent - 0.025), 1)
            drone.target_segment_id = target.id
            drone.task = f"{target.name} · {target.focus_label}"

    async def step(self) -> PlatformSnapshot:
        async with self._lock:
            if self._running:
                self._tick += 1
                self.race.elapsed_seconds += self.race.simulation_speed
                self._update_athletes()
                self._recalculate_segments()
                self._update_drones()
            return self._build_snapshot()

    def _build_snapshot(self) -> PlatformSnapshot:
        open_alerts = sum(alert.status == "new" for alert in self.alerts)
        high_risk = sum(max(segment.crowd_risk, segment.health_risk) >= 0.72 for segment in self.segments)
        return PlatformSnapshot(
            generated_at=datetime.now(timezone.utc),
            race=self.race,
            segments=self.segments,
            athletes=self.athletes,
            drones=self.drones,
            alerts=list(reversed(self.alerts[-20:])),
            stats=PlatformStats(
                online_athletes=sum(athlete.status != "finished" for athlete in self.athletes),
                active_drones=len(self.drones),
                open_alerts=open_alerts,
                high_risk_segments=high_risk,
            ),
        )

    async def snapshot(self) -> PlatformSnapshot:
        async with self._lock:
            return self._build_snapshot()

    async def inject_event(self, event_type: str, segment_id: str | None) -> AlertState:
        async with self._lock:
            segment = next((item for item in self.segments if item.id == segment_id), None)
            if segment is None:
                segment = max(self.segments, key=lambda item: max(item.crowd_risk, item.health_risk))
            candidates = [athlete for athlete in self.athletes if athlete.segment_id == segment.id and athlete.status != "finished"]
            athlete = self._random.choice(candidates) if candidates else None
            self._event_counter += 1
            alert_id = f"EVT-{self._event_counter + 1:04d}"

            if event_type == "crowd":
                self._risk_boosts[segment.id] = {"crowd": 0.38, "health": 0.0, "until": self._tick + 35}
                level, title = "warning", "检测到人群聚集趋势"
                message = f"{segment.name}的人群密度持续上升，已提高聚集监测优先级。"
            elif event_type == "fall":
                self._risk_boosts[segment.id] = {"crowd": 0.05, "health": 0.42, "until": self._tick + 45}
                level, title = "critical", "疑似运动员跌倒"
                message = f"{segment.name}发现疑似跌倒，已请求无人机近距复核。"
                if athlete:
                    athlete.status = "fallen"
                    athlete.heart_rate = 186
            else:
                self._risk_boosts[segment.id] = {"crowd": 0.0, "health": 0.34, "until": self._tick + 40}
                level, title = "warning", "穿戴设备体征异常"
                message = f"{segment.name}出现持续高心率，已提高个体安全监测优先级。"
                if athlete:
                    athlete.status = "warning"
                    athlete.heart_rate = 192

            alert = AlertState(
                id=alert_id,
                created_at=datetime.now(timezone.utc),
                level=level,
                event_type=event_type,
                title=title,
                message=message,
                segment_id=segment.id,
                athlete_id=athlete.id if athlete and event_type != "crowd" else None,
            )
            self.alerts.append(alert)
            self._recalculate_segments()
            return alert

    async def acknowledge_alert(self, alert_id: str) -> AlertState | None:
        async with self._lock:
            alert = next((item for item in self.alerts if item.id == alert_id), None)
            if alert:
                alert.status = "acknowledged"
            return alert

    async def control(self, action: str) -> PlatformSnapshot:
        async with self._lock:
            if action == "reset":
                self._reset_state()
                self._running = False
                self.race.status = "paused"
            elif action == "pause":
                self._running = False
                self.race.status = "paused"
            else:
                self._running = True
                self.race.status = "running"
            return self._build_snapshot()

    async def run(self, publish: PublishCallback, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            snapshot = await self.step()
            await publish(snapshot.model_dump(mode="json"))
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=1.0)
            except TimeoutError:
                pass
