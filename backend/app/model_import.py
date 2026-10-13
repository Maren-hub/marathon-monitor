"""Local 3D Tiles / OSGB ZIP import for the Cesium prototype.

Uploads are streamed to disk, unpacked with path and size checks, and only
known model asset extensions are served. Raw OSGB needs the separately
installed 3dtile converter; a ZIP is never presented as a ready model before
the conversion output has passed basic validation.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import shutil
import stat
import subprocess
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
MODEL_ROOT = ROOT / "data" / "model_assets"
REGISTRY_PATH = ROOT / "data" / "model_registry.json"
LEGACY_TILESET = ROOT / "frontend" / "public" / "3dtiles" / "nanlin" / "tileset.json"
DEFAULT_CONVERTER = ROOT.parent / "tools" / "3dtiles-converter" / "v0.4" / "3dtile.exe"
MAX_ARCHIVE_BYTES = 12 * 1024**3
MAX_UNPACKED_BYTES = 45 * 1024**3
MAX_MEMBERS = 40000
ASSET_SUFFIXES = {".json", ".b3dm", ".pnts", ".i3dm", ".cmpt", ".glb", ".gltf", ".bin", ".png", ".jpg", ".jpeg", ".webp", ".ktx", ".ktx2", ".subtree"}
JOBS: dict[str, dict[str, Any]] = {}
_import_lock = asyncio.Lock()


class ModelImportError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_registry() -> list[dict]:
    if not REGISTRY_PATH.exists():
        return []
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except (ValueError, OSError):
        return []


def _write_registry(models: list[dict]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = REGISTRY_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(models, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(REGISTRY_PATH)


def list_models() -> list[dict]:
    models = []
    if LEGACY_TILESET.is_file():
        models.append({
            "id": "nanlin", "name": "校园三维实景（已接入）", "format": "3D Tiles",
            "url": "/3dtiles/nanlin/tileset.json", "source": "已有转换成果",
        })
    for item in _read_registry():
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        tileset = MODEL_ROOT / item["id"] / "ready" / "tileset.json"
        if tileset.is_file():
            models.append({
                "id": item["id"], "name": item.get("name", item["id"]),
                "format": item.get("format", "3D Tiles"),
                "url": f"/api/models/assets/{item['id']}/tileset.json",
                "source": item.get("source", "导入模型"),
                "created_at": item.get("created_at"),
            })
    return models


def _safe_members(archive: zipfile.ZipFile) -> list[tuple[zipfile.ZipInfo, PurePosixPath]]:
    members = archive.infolist()
    if not members or len(members) > MAX_MEMBERS:
        raise ModelImportError("压缩包为空或文件数量过多（上限 4 万个）")
    total = 0
    result = []
    seen = set()
    for info in members:
        raw = info.filename.replace("\\", "/")
        path = PurePosixPath(raw)
        if not raw or raw.startswith("/") or ":" in raw or any(part in {"..", "."} for part in path.parts):
            raise ModelImportError("压缩包含不安全的文件路径，已停止导入")
        if stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF):
            raise ModelImportError("压缩包含符号链接，已停止导入")
        if info.flag_bits & 1:
            raise ModelImportError("暂不支持加密压缩包")
        if raw.lower() in seen:
            raise ModelImportError("压缩包中存在重名文件，已停止导入")
        seen.add(raw.lower())
        total += info.file_size
        if total > MAX_UNPACKED_BYTES:
            raise ModelImportError("解压后预计超过 45 GB，请先精简模型")
        result.append((info, path))
    return result


def _classify(members: list[tuple[zipfile.ZipInfo, PurePosixPath]]) -> str:
    names = [path.name.lower() for _, path in members]
    if "tileset.json" in names:
        return "3D Tiles"
    if "metadata.xml" in names and any(name.endswith(".osgb") for name in names):
        return "OSGB"
    raise ModelImportError("未找到 tileset.json，也未找到 OSGB 模型及 metadata.xml；无法识别该模型包")


def _validate_tileset(directory: Path) -> None:
    boundary = directory.resolve()
    visited = set()
    references = 0

    def visit_manifest(path: Path) -> None:
        nonlocal references
        if path in visited:
            return
        visited.add(path)
        if len(visited) > 1000:
            raise ModelImportError("模型索引层数异常，已停止检查")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ModelImportError(f"模型索引缺失或无法读取：{path.name}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("root"), dict) or not isinstance(data.get("asset"), dict):
            raise ModelImportError("tileset.json 结构不完整")

        def visit_node(node: dict) -> None:
            nonlocal references
            if not isinstance(node, dict) or not isinstance(node.get("boundingVolume"), dict):
                raise ModelImportError("模型缺少有效的空间范围")
            box = node["boundingVolume"].get("box")
            if box is not None and (not isinstance(box, list) or len(box) != 12 or any(not isinstance(x, (int, float)) or not math.isfinite(x) or abs(x) > 1e20 for x in box)):
                raise ModelImportError("模型空间范围异常，需检查转换坐标或空瓦片")
            contents = []
            if node.get("content"):
                contents.append(node["content"])
            contents.extend(node.get("contents") or [])
            for content in contents:
                if not isinstance(content, dict):
                    raise ModelImportError("模型瓦片索引不完整")
                uri = content.get("uri") or content.get("url")
                if not isinstance(uri, str) or not uri:
                    raise ModelImportError("模型瓦片缺少文件地址")
                parsed = urlsplit(uri)
                if parsed.scheme or parsed.netloc:
                    raise ModelImportError("模型引用了外部瓦片；请提供完整的本地 ZIP")
                asset = (path.parent / unquote(parsed.path)).resolve()
                if not asset.is_relative_to(boundary) or not asset.is_file():
                    raise ModelImportError("瓦片索引引用的文件不存在；请提供完整模型包，而非仅 tileset.json")
                references += 1
                if references > 50000:
                    raise ModelImportError("模型引用的文件数量过多")
                if asset.name.lower() == "tileset.json":
                    visit_manifest(asset)
            for child in node.get("children") or []:
                visit_node(child)

        root = data["root"]
        if not root.get("content") and not root.get("contents") and not root.get("children"):
            raise ModelImportError("tileset.json 没有可显示的模型内容")
        visit_node(root)

    visit_manifest(directory / "tileset.json")
    if not references:
        raise ModelImportError("模型包中没有实际瓦片文件")


def _extract(archive: zipfile.ZipFile, members: list[tuple[zipfile.ZipInfo, PurePosixPath]], target: Path, job: dict) -> None:
    target.mkdir(parents=True)
    actual_total = 0
    for index, (info, path) in enumerate(members, start=1):
        output = target.joinpath(*path.parts)
        if info.is_dir():
            output.mkdir(parents=True, exist_ok=True)
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, output.open("wb") as destination:
            while chunk := source.read(1024 * 1024):
                actual_total += len(chunk)
                if actual_total > MAX_UNPACKED_BYTES:
                    raise ModelImportError("实际解压数据超过 45 GB，已停止导入")
                destination.write(chunk)
        if index % 100 == 0 or index == len(members):
            job.update(stage="extracting", message=f"正在解压：{index}/{len(members)} 个文件", progress=round(index / len(members) * 70))


def _find_tileset(root: Path) -> Path:
    candidates = sorted(root.rglob("tileset.json"), key=lambda path: (len(path.relative_to(root).parts), str(path)))
    if not candidates:
        raise ModelImportError("转换没有生成 tileset.json")
    return candidates[0].parent


def _find_osgb_root(root: Path) -> Path:
    candidates = sorted(root.rglob("metadata.xml"), key=lambda path: len(path.relative_to(root).parts))
    for metadata in candidates:
        if any(metadata.parent.rglob("*.osgb")):
            return metadata.parent
    raise ModelImportError("没有找到同时包含 metadata.xml 和 OSGB 文件的目录")


def _cleanup_intermediates(job_dir: Path) -> None:
    """Remove only copies created inside this import's own workspace folder."""
    root = MODEL_ROOT.resolve()
    resolved_job = job_dir.resolve()
    if resolved_job.parent != root:
        raise ModelImportError("临时目录超出模型工作区，已停止清理")
    (resolved_job / "source.zip").unlink(missing_ok=True)
    for name in ("extracted", "converted"):
        candidate = (resolved_job / name).resolve()
        if candidate.parent != resolved_job:
            raise ModelImportError("临时目录路径异常，已停止清理")
        if candidate.is_dir():
            shutil.rmtree(candidate)


def _process_archive(job: dict, archive_path: Path) -> None:
    job_dir = archive_path.parent
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = _safe_members(archive)
            kind = _classify(members)
            converter = Path(os.environ.get("MODEL_OSGB_CONVERTER", DEFAULT_CONVERTER))
            if kind == "OSGB" and not converter.is_file():
                raise ModelImportError("这台电脑缺少 OSGB 转换工具；请安装 3dtile 或让同伴提供转换后的 3D Tiles 包")
            unpacked = sum(info.file_size for info, _ in members)
            required = unpacked * (2 if kind == "OSGB" else 1) + 2 * 1024**3
            if shutil.disk_usage(job_dir).free < required:
                raise ModelImportError("磁盘空间不足：原始 OSGB 需要解压空间和转换后的额外空间")
            job.update(stage="extracting", message=f"识别为 {kind}，准备解压", progress=0, format=kind)
            _extract(archive, members, job_dir / "extracted", job)
        if kind == "OSGB":
            source = _find_osgb_root(job_dir / "extracted")
            output = job_dir / "converted"
            output.mkdir()
            job.update(stage="converting", message="OSGB 正在转换成 3D Tiles；大模型可能需要较长时间", progress=75)
            with (job_dir / "conversion.log").open("wb") as log:
                result = subprocess.run(
                    [str(converter), "--format", "osgb", "--input", str(source), "--output", str(output)],
                    cwd=converter.parent, stdout=log, stderr=subprocess.STDOUT, check=False,
                )
            if result.returncode != 0:
                raise ModelImportError(f"OSGB 转换失败（退出码 {result.returncode}）；请检查模型的坐标元数据和转换日志")
            ready_source = _find_tileset(output)
        else:
            ready_source = _find_tileset(job_dir / "extracted")
        _validate_tileset(ready_source)
        ready = job_dir / "ready"
        ready_source.rename(ready)
        # Complete the registry only after all processing and validation succeeds.
        model = {
            "id": job["id"], "name": job["name"], "format": kind,
            "source": job["filename"], "created_at": _now(),
        }
        _write_registry([*_read_registry(), model])
        job.update(stage="ready", message="模型已接入，可以切换显示；仍请检查坐标和细节", progress=100, model=model)
        try:
            _cleanup_intermediates(job_dir)
        except (OSError, ModelImportError):
            job["message"] = "模型可用，但临时副本未能自动清理；请检查剩余磁盘空间"
    except (zipfile.BadZipFile, OSError, ModelImportError, ValueError, TypeError, KeyError) as exc:
        job.update(stage="error", message=str(exc), progress=0)
        try:
            _cleanup_intermediates(job_dir)
        except (OSError, ModelImportError):
            pass


async def start_import(archive_path: Path, filename: str) -> dict:
    async with _import_lock:
        job_id = archive_path.parent.name
        job = JOBS[job_id]
        job.update(stage="checking", message="正在检查模型包")
        try:
            await asyncio.to_thread(_process_archive, job, archive_path)
        except Exception as exc:
            job.update(stage="error", message=f"后台处理意外中断：{exc}", progress=0)
    return job


def new_import_path() -> tuple[str, Path]:
    job_id = uuid.uuid4().hex[:12]
    job_dir = MODEL_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    return job_id, job_dir / "source.zip"


def register_uploaded_job(job_id: str, filename: str) -> dict:
    job = {
        "id": job_id, "name": Path(filename).stem[:80] or "导入模型",
        "filename": Path(filename).name, "stage": "queued",
        "message": "文件已收到，等待检查", "progress": 0, "created_at": _now(),
    }
    JOBS[job_id] = job
    return job


def model_asset(model_id: str, asset_path: str) -> Path:
    if not any(item["id"] == model_id for item in list_models() if item["id"] != "nanlin"):
        raise FileNotFoundError("模型不存在")
    root = (MODEL_ROOT / model_id / "ready").resolve()
    target = (root / asset_path).resolve()
    if not target.is_relative_to(root) or target.suffix.lower() not in ASSET_SUFFIXES or not target.is_file():
        raise FileNotFoundError("模型资源不存在")
    return target
