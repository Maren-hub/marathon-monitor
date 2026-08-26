from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = PROJECT_ROOT / "data" / "pipeline_sample.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="批量发送马拉松多源数据到自动处理管道")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE, help="标准JSON批次文件")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/api/pipeline/ingest",
        help="后端自动数据接入地址",
    )
    args = parser.parse_args()

    payload = args.file.read_bytes()
    request = Request(
        args.url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"后端拒绝了数据（HTTP {exc.code}）：{detail}") from exc
    except URLError as exc:
        raise SystemExit("无法连接后端，请先启动后端服务。") from exc

    print("接收数量：", json.dumps(result["accepted"], ensure_ascii=False))
    print("累计存储：", json.dumps(result["stored"], ensure_ascii=False))
    print("自动处理结果：")
    for item in result["results"]:
        print(
            f"- {item['window_start']} {item['segment_id']} | "
            f"状态={item['record_status']} | "
            f"聚集风险={item['crowd_risk']} | 健康风险={item['health_risk']} | "
            f"重点={item['focus_label']} | 建议={','.join(item['recommended_units'])}"
        )


if __name__ == "__main__":
    main()
