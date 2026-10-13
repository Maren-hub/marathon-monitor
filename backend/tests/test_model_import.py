import json
import zipfile

import backend.app.model_import as model_import


def _tileset() -> bytes:
    return json.dumps({
        "asset": {"version": "1.0"},
        "root": {
            "boundingVolume": {"box": [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]},
            "geometricError": 1,
            "content": {"uri": "tile.b3dm"},
        },
    }).encode()


def test_import_complete_3d_tiles_zip(tmp_path, monkeypatch):
    monkeypatch.setattr(model_import, "MODEL_ROOT", tmp_path / "models")
    monkeypatch.setattr(model_import, "REGISTRY_PATH", tmp_path / "registry.json")
    job_id, target = model_import.new_import_path()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("campus/tileset.json", _tileset())
        archive.writestr("campus/tile.b3dm", b"sample-tile")
    model_import.register_uploaded_job(job_id, "campus.zip")
    result = model_import.JOBS[job_id]
    model_import._process_archive(result, target)
    assert result["stage"] == "ready"
    assert (tmp_path / "models" / job_id / "ready" / "tileset.json").is_file()
    assert model_import.model_asset(job_id, "tile.b3dm").read_bytes() == b"sample-tile"
    assert not target.exists()


def test_raw_osgb_needs_converter_and_is_not_marked_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(model_import, "MODEL_ROOT", tmp_path / "models")
    monkeypatch.setattr(model_import, "REGISTRY_PATH", tmp_path / "registry.json")
    monkeypatch.setenv("MODEL_OSGB_CONVERTER", str(tmp_path / "missing.exe"))
    job_id, target = model_import.new_import_path()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("terra_osgbs/metadata.xml", "<ModelMetadata/>")
        archive.writestr("terra_osgbs/A/A.osgb", b"osgb")
    model_import.register_uploaded_job(job_id, "raw.zip")
    result = model_import.JOBS[job_id]
    model_import._process_archive(result, target)
    assert result["stage"] == "error"
    assert not any(item["id"] == job_id for item in model_import.list_models())


def test_zip_path_traversal_is_rejected(tmp_path):
    target = tmp_path / "bad.zip"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("../escape.txt", "not allowed")
    with zipfile.ZipFile(target) as archive:
        try:
            model_import._safe_members(archive)
        except model_import.ModelImportError:
            pass
        else:
            raise AssertionError("Zip-slip member was accepted")
