"""Small dependency-free check for the model importer; never converts a large model."""

from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backend.app.model_import as model_import  # noqa: E402


workspace = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(dir=workspace / "data") as temporary:
    root = Path(temporary)
    assert root.resolve().is_relative_to(workspace.resolve())
    model_import.MODEL_ROOT = root / "models"
    model_import.REGISTRY_PATH = root / "registry.json"
    job_id, target = model_import.new_import_path()
    tileset = {
        "asset": {"version": "1.0"},
        "root": {
            "boundingVolume": {"box": [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]},
            "geometricError": 1,
            "content": {"uri": "tile.b3dm"},
        },
    }
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("campus/tileset.json", json.dumps(tileset))
        archive.writestr("campus/tile.b3dm", b"test-data")
    model_import.register_uploaded_job(job_id, "campus.zip")
    print("Starting tiny 3D Tiles ZIP import", flush=True)
    job = model_import.JOBS[job_id]
    model_import._process_archive(job, target)
    assert job["stage"] == "ready", job
    assert model_import.model_asset(job_id, "tile.b3dm").read_bytes() == b"test-data"
    print("3D Tiles ZIP import: PASS")

    bad_id, bad_target = model_import.new_import_path()
    with zipfile.ZipFile(bad_target, "w") as archive:
        archive.writestr("../escape.txt", "bad")
    model_import.register_uploaded_job(bad_id, "bad.zip")
    bad_job = model_import.JOBS[bad_id]
    model_import._process_archive(bad_job, bad_target)
    assert bad_job["stage"] == "error", bad_job
    print("Unsafe ZIP rejection: PASS")
