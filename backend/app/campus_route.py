"""Validate and persist a campus route drawn in GIS software.

A route whose segment identifiers are exactly S1-S5 can be used as the spatial
carrier for the prototype simulation.  The simulator still owns the synthetic
race time and risk values; the map projects those values onto the five campus
segments instead of pretending that the model-traced line is a surveyed race.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


ROOT = Path(__file__).resolve().parents[2]
ROUTE_FILE = ROOT / "data" / "campus_route_import.json"
MODEL_TRACED_ROUTE_FILE = ROOT / "data" / "nanlin_road_loop_model_traced.geojson"
MODEL_TRACED_SITES_FILE = ROOT / "data" / "campus_medical_sites.geojson"
MAX_ROUTE_FILE_BYTES = 2 * 1024 * 1024
MAX_FEATURES = 100
MAX_VERTICES = 3000
BOUNDS = (118.79, 32.06, 118.84, 32.11)  # broad Campus-area guard, not a survey boundary
SIMULATION_SEGMENT_IDS = {f"S{index}" for index in range(1, 6)}


class CampusRouteError(ValueError):
    pass


def empty_course() -> dict:
    return {
        "version": "geojson-import-v1",
        "route_filename": None,
        "route_updated_at": None,
        "sites_filename": None,
        "sites_updated_at": None,
        "segments": [],
        "sites": [],
        "route_length_km": 0.0,
        "simulation_linked": False,
        "status": "未导入；旧手绘候选线已停止展示",
        "note": "仅为空间展示，尚未与模拟赛事赛段、运动员和报警数据关联。",
    }


def load_course() -> dict:
    if ROUTE_FILE.is_file():
        return {**empty_course(), **json.loads(ROUTE_FILE.read_text(encoding="utf-8"))}
    # A bundled, model-traced example is visible on a fresh team checkout.
    # A later user import still takes precedence over this demonstration line.
    if ROUTE_FILE == ROOT / "data" / "campus_route_import.json" and MODEL_TRACED_ROUTE_FILE.is_file():
        segments = parse_course_geojson(MODEL_TRACED_ROUTE_FILE.read_bytes(), "route")
        sites = (
            parse_course_geojson(MODEL_TRACED_SITES_FILE.read_bytes(), "sites")
            if MODEL_TRACED_SITES_FILE.is_file()
            else []
        )
        simulation_linked = {item["id"] for item in segments} == SIMULATION_SEGMENT_IDS
        return {
            **empty_course(),
            "route_filename": "campus_road_loop_model_traced.geojson",
            "sites_filename": MODEL_TRACED_SITES_FILE.name if sites else None,
            "segments": segments,
            "sites": sites,
            "route_length_km": round(sum(_length_km(item["coordinates"]) for item in segments), 3),
            "simulation_linked": simulation_linked,
            "status": "模型道路目视核线·待现场核查",
            "note": "依据校园倾斜摄影模型的可见道路人工取点；已按S1-S5承载模拟运动员、无人机与报警位置，并配置3处拟设医疗保障点，但未完成实地通行、坐标和救护条件核查。",
        }
    return empty_course()


def _position(value: object) -> list[float]:
    if not isinstance(value, list) or len(value) < 2:
        raise CampusRouteError("坐标应为 [经度, 纬度]；请在 QGIS 中导出 EPSG:4326 GeoJSON")
    longitude, latitude = value[:2]
    if isinstance(longitude, bool) or isinstance(latitude, bool):
        raise CampusRouteError("坐标必须是数字")
    try:
        longitude, latitude = float(longitude), float(latitude)
    except (TypeError, ValueError) as error:
        raise CampusRouteError("坐标必须是数字") from error
    if not math.isfinite(longitude) or not math.isfinite(latitude):
        raise CampusRouteError("坐标不能包含无穷值或空值")
    west, south, east, north = BOUNDS
    if not (west <= longitude <= east and south <= latitude <= north):
        raise CampusRouteError("坐标不在当前校园场景范围内；请核查图层位置与 EPSG:4326 坐标系")
    return [round(longitude, 8), round(latitude, 8)]


def _model_heights(line: list) -> list[float] | None:
    """Keep model-surface heights only when every route vertex supplies one."""
    has_height = [isinstance(position, list) and len(position) >= 3 for position in line]
    if not any(has_height):
        return None
    if not all(has_height):
        raise CampusRouteError("三维路线的每个节点都必须提供高度；普通路线请全部使用经纬度两列")
    heights = []
    for position in line:
        value = position[2]
        if isinstance(value, bool):
            raise CampusRouteError("路线高度必须是有效数字")
        try:
            height = float(value)
        except (TypeError, ValueError) as error:
            raise CampusRouteError("路线高度必须是有效数字") from error
        if not math.isfinite(height) or not -10000 <= height <= 10000:
            raise CampusRouteError("路线高度超出合理范围")
        heights.append(round(height, 2))
    return heights


def _point_height(position: object) -> float | None:
    """Retain an optional model-surface height supplied by a Point feature."""
    if not isinstance(position, list) or len(position) < 3:
        return None
    value = position[2]
    if isinstance(value, bool):
        raise CampusRouteError("点位高度必须是有效数字")
    try:
        height = float(value)
    except (TypeError, ValueError) as error:
        raise CampusRouteError("点位高度必须是有效数字") from error
    if not math.isfinite(height) or not -10000 <= height <= 10000:
        raise CampusRouteError("点位高度超出合理范围")
    return round(height, 2)


def _text(value: object, fallback: str, limit: int = 80) -> str:
    value = str(value).strip() if value is not None else ""
    return value[:limit] or fallback


def _features(raw: bytes) -> list[dict]:
    if not raw or len(raw) > MAX_ROUTE_FILE_BYTES:
        raise CampusRouteError("请选择不超过 2 MB 的 GeoJSON 文件")
    try:
        document = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CampusRouteError("文件不是有效的 UTF-8 GeoJSON") from error
    if not isinstance(document, dict):
        raise CampusRouteError("GeoJSON 顶层格式无效")
    crs = document.get("crs")
    if crs and not any(name in json.dumps(crs, ensure_ascii=False).upper() for name in ("4326", "CRS84")):
        raise CampusRouteError("请在 QGIS 导出时选择 WGS84 / EPSG:4326")
    if document.get("type") == "FeatureCollection":
        features = document.get("features")
    elif document.get("type") == "Feature":
        features = [document]
    else:
        raise CampusRouteError("只接受 GeoJSON FeatureCollection 或 Feature")
    if not isinstance(features, list) or not 1 <= len(features) <= MAX_FEATURES:
        raise CampusRouteError("GeoJSON 应包含 1–100 个要素")
    if any(not isinstance(feature, dict) or feature.get("type") != "Feature" for feature in features):
        raise CampusRouteError("GeoJSON 中存在无效要素")
    return features


def _length_km(coordinates: list[list[float]]) -> float:
    distance = 0.0
    for first, second in zip(coordinates, coordinates[1:]):
        lon1, lat1 = map(math.radians, first)
        lon2, lat2 = map(math.radians, second)
        term = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        distance += 2 * 6371.0088 * math.atan2(math.sqrt(term), math.sqrt(max(0.0, 1 - term)))
    return distance


def parse_course_geojson(raw: bytes, kind: Literal["route", "sites"]) -> list[dict]:
    features = _features(raw)
    parsed: list[dict] = []
    vertex_count = 0
    for feature in features:
        geometry = feature.get("geometry") or {}
        properties = feature.get("properties") or {}
        if not isinstance(geometry, dict) or not isinstance(properties, dict):
            raise CampusRouteError("要素的 geometry 或 properties 无效")
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates")
        if kind == "route":
            lines = coordinates if geometry_type == "MultiLineString" else [coordinates] if geometry_type == "LineString" else None
            if not isinstance(lines, list):
                raise CampusRouteError("路线文件应包含 LineString 或 MultiLineString 线要素")
            for line in lines:
                if not isinstance(line, list) or len(line) < 2:
                    raise CampusRouteError("每条路线至少需要两个坐标点")
                vertex_count += len(line)
                if vertex_count > MAX_VERTICES:
                    raise CampusRouteError("路线点位超过 3000 个，请先在 GIS 软件中简化")
                number = len(parsed) + 1
                segment = {
                    "id": _text(properties.get("segment_id") or properties.get("id"), f"C{number}", 20),
                    "name": _text(properties.get("name") or properties.get("名称"), f"路线第{number}段"),
                    "task": _text(properties.get("task") or properties.get("说明"), "待现场核查"),
                    "coordinates": [_position(position) for position in line],
                }
                heights = _model_heights(line)
                if heights is not None:
                    segment["heights_m"] = heights
                parsed.append(segment)
        else:
            if geometry_type != "Point":
                raise CampusRouteError("保障点文件应只包含 Point 点要素")
            number = len(parsed) + 1
            raw_kind = _text(properties.get("kind") or properties.get("类型"), "other", 20).lower()
            site_kind = {
                "起终点": "start", "医疗": "medical", "补给": "water", "观察": "marshal",
            }.get(raw_kind, raw_kind)
            if site_kind not in {"start", "medical", "water", "marshal", "other"}:
                site_kind = "other"
            site = {
                "id": _text(properties.get("site_id") or properties.get("id"), f"P{number}", 20),
                "kind": site_kind,
                "name": _text(properties.get("name") or properties.get("名称"), f"候选点位{number}"),
                "reason": _text(properties.get("note") or properties.get("说明"), "位置待现场核查", 160),
                "coordinate": _position(coordinates),
            }
            height = _point_height(coordinates)
            if height is not None:
                site["height_m"] = height
            parsed.append(site)
    if not parsed:
        raise CampusRouteError("文件没有可导入的要素")
    ids = [item["id"] for item in parsed]
    if len(ids) != len(set(ids)):
        raise CampusRouteError("要素编号重复，请在 QGIS 中修改 segment_id 或 site_id")
    return parsed


def save_course_geojson(raw: bytes, kind: Literal["route", "sites"], filename: str) -> dict:
    parsed = parse_course_geojson(raw, kind)
    course = load_course()
    now = datetime.now(timezone.utc).isoformat()
    clean_filename = Path(filename.replace("\\", "/")).name[:120]
    if kind == "route":
        course["segments"] = parsed
        course["route_filename"] = clean_filename
        course["route_updated_at"] = now
        course["route_length_km"] = round(sum(_length_km(item["coordinates"]) for item in parsed), 3)
        course["simulation_linked"] = {item["id"] for item in parsed} == SIMULATION_SEGMENT_IDS
    else:
        course["sites"] = parsed
        course["sites_filename"] = clean_filename
        course["sites_updated_at"] = now
    course["status"] = "外部绘制路线·待现场核查" if course["segments"] else "仅导入点位；尚无路线"
    course["note"] = (
        "路线已按S1-S5与模拟实体建立空间映射；仍需现场核查道路、坐标与保障条件。"
        if course.get("simulation_linked")
        else "路线仅作空间展示；如需承载模拟数据，请将五段编号设为S1、S2、S3、S4、S5。"
    )
    ROUTE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = ROUTE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(course, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(ROUTE_FILE)
    return course
