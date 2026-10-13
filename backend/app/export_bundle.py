"""Create a self-contained, clearly labelled prototype result bundle."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from html import escape


def _csv_bytes(rows: list[dict], fields: list[str]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in fields})
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def create_export_bundle(state: dict, pipeline_results: list[dict] | None = None) -> bytes:
    snapshot = state["snapshot"]
    segments = [dict(item) for item in snapshot["segments"]]
    pipeline_by_segment = {
        item["segment_id"]: item for item in (pipeline_results or [])
        if item.get("record_status") == "usable"
    }
    for segment in segments:
        result = pipeline_by_segment.get(segment["id"])
        segment["data_source"] = "pipeline" if result else "simulation-fallback"
        if result:
            for key in ("crowd_risk", "health_risk", "focus", "focus_label", "monitoring_tasks"):
                if result.get(key) is not None:
                    segment[key] = result[key]
            if result.get("uav_person_count") is not None:
                segment["athlete_count"] = result["uav_person_count"]
    if pipeline_results is None:
        for segment in segments:
            segment["data_source"] = "simulation"
    snapshot["segments"] = segments

    alerts = state["alerts"]
    generated_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "product": "智跑慧巡",
        "generated_at": generated_at,
        "mode": "pipeline" if pipeline_results is not None else "simulation",
        "note": "演示原型导出。自动接入模式仅覆盖有可用管道结果的赛段；其他赛段仍为模拟值。报警和体征历史来自模拟器，不代表真实赛事记录。",
        "segment_sources": {item["id"]: item["data_source"] for item in segments},
        "alert_count": len(alerts),
    }
    segment_fields = ["id", "name", "start_km", "end_km", "athlete_count", "crowd_risk", "health_risk", "focus", "focus_label", "data_source"]
    alert_fields = ["id", "created_at", "event_type", "level", "segment_id", "athlete_id", "title", "status", "handling_action", "assigned_unit", "response_seconds", "resolution_seconds"]

    segment_rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(item.get(key, '')))}</td>" for key in ("id", "name", "athlete_count", "crowd_risk", "health_risk", "data_source")) + "</tr>"
        for item in segments
    )
    alert_rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(item.get(key, '')))}</td>" for key in ("created_at", "event_type", "segment_id", "title", "status")) + "</tr>"
        for item in alerts if item.get("event_type") != "system"
    )
    html = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>智跑慧巡 · 成果快照</title>
<style>body{{font:15px/1.6 'Microsoft YaHei',sans-serif;max-width:1100px;margin:40px auto;color:#183040}}h1{{color:#087c83}}table{{border-collapse:collapse;width:100%;margin:12px 0 30px}}th,td{{border:1px solid #cad7dc;padding:7px;text-align:left}}th{{background:#eaf5f6}}.note{{padding:14px;background:#fff3d7}}</style>
<h1>智跑慧巡 · 赛事成果快照</h1><p>导出时间（UTC）：{escape(generated_at)}</p>
<p>赛事：{escape(str(snapshot['race']['name']))}　模拟赛时：{escape(str(snapshot['race']['elapsed_seconds']))} 秒　报警记录：{len(alerts)} 条</p>
<p class="note">{escape(manifest['note'])}</p>
<h2>赛段风险</h2><table><tr><th>编号</th><th>名称</th><th>人数</th><th>聚集风险 0–1</th><th>健康风险 0–1</th><th>数据来源</th></tr>{segment_rows}</table>
<h2>报警与处置</h2><table><tr><th>时间</th><th>类型</th><th>赛段</th><th>标题</th><th>状态</th></tr>{alert_rows}</table></html>"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("snapshot.json", json.dumps(snapshot, ensure_ascii=False, indent=2))
        archive.writestr("segments.json", json.dumps(segments, ensure_ascii=False, indent=2))
        archive.writestr("alerts.json", json.dumps(alerts, ensure_ascii=False, indent=2))
        archive.writestr("health_history.json", json.dumps(state["health_history"], ensure_ascii=False, indent=2))
        archive.writestr("segments.csv", _csv_bytes(segments, segment_fields))
        archive.writestr("alerts.csv", _csv_bytes(alerts, alert_fields))
        archive.writestr("report.html", html)
    return buffer.getvalue()
