"""Repair bounding volumes produced for empty OSGB tiles.

Some OSGB datasets contain edge tiles without vertices. Older converters keep
those nodes and write sentinel values around 1e38 into their bounding boxes.
Cesium may then calculate an unusable camera range. This script removes empty
leaf nodes and rebuilds invalid parent boxes from their valid descendants.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path


def valid_box(box: object) -> bool:
    return (
        isinstance(box, list)
        and len(box) == 12
        and all(isinstance(value, (int, float)) for value in box)
        and all(math.isfinite(value) and abs(value) < 1e20 for value in box)
    )


def box_bounds(box: list[float]) -> tuple[list[float], list[float]]:
    center = box[:3]
    extents = [
        abs(box[3]) + abs(box[6]) + abs(box[9]),
        abs(box[4]) + abs(box[7]) + abs(box[10]),
        abs(box[5]) + abs(box[8]) + abs(box[11]),
    ]
    return (
        [center[index] - extents[index] for index in range(3)],
        [center[index] + extents[index] for index in range(3)],
    )


def union_boxes(boxes: list[list[float]]) -> list[float]:
    bounds = [box_bounds(box) for box in boxes]
    minimum = [min(item[0][index] for item in bounds) for index in range(3)]
    maximum = [max(item[1][index] for item in bounds) for index in range(3)]
    center = [(minimum[index] + maximum[index]) / 2 for index in range(3)]
    extents = [(maximum[index] - minimum[index]) / 2 for index in range(3)]
    return [
        center[0], center[1], center[2],
        extents[0], 0.0, 0.0,
        0.0, extents[1], 0.0,
        0.0, 0.0, extents[2],
    ]


def repair_node(node: dict, counters: dict[str, int]) -> dict | None:
    repaired_children = []
    for child in node.get("children", []):
        repaired = repair_node(child, counters)
        if repaired is not None:
            repaired_children.append(repaired)

    if repaired_children:
        node["children"] = repaired_children
    else:
        node.pop("children", None)

    box = node.get("boundingVolume", {}).get("box")
    if valid_box(box):
        return node

    counters["invalid_nodes"] += 1
    node.pop("content", None)
    child_boxes = [child["boundingVolume"]["box"] for child in repaired_children]
    if not child_boxes:
        counters["removed_empty_leaves"] += 1
        return None

    node["boundingVolume"] = {"box": union_boxes(child_boxes)}
    counters["rebuilt_parent_boxes"] += 1
    return node


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_with_backup(path: Path, data: dict) -> None:
    backup = path.with_suffix(path.suffix + ".original")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block-tileset", required=True, type=Path)
    parser.add_argument("--root-tileset", type=Path)
    args = parser.parse_args()

    counters = {
        "invalid_nodes": 0,
        "removed_empty_leaves": 0,
        "rebuilt_parent_boxes": 0,
    }
    block_data = load_json(args.block_tileset)
    repaired_root = repair_node(block_data["root"], counters)
    if repaired_root is None:
        raise RuntimeError("No valid tiles remain after repair")
    block_data["root"] = repaired_root
    write_json_with_backup(args.block_tileset, block_data)

    if args.root_tileset:
        root_data = load_json(args.root_tileset)
        block_box = repaired_root["boundingVolume"]["box"]
        root_data["root"]["boundingVolume"] = {"box": block_box}
        for child in root_data["root"].get("children", []):
            child["boundingVolume"] = {"box": block_box}
        write_json_with_backup(args.root_tileset, root_data)

    print(json.dumps(counters, ensure_ascii=False))


if __name__ == "__main__":
    main()
