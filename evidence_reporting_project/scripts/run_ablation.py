from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.io_utils import dump_json
from src.pipeline import run_ablation


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dates", default="20220601,20220603,20220604")
    parser.add_argument("--mode", default="A", choices=["A", "B"])
    parser.add_argument("--llm-provider", default="mock", choices=["mock", "deepseek"])
    args = parser.parse_args()
    dates = [item.strip() for item in args.dates.split(",") if item.strip()]
    result = run_ablation(dates, args.mode, args.llm_provider)
    dump_json(f"outputs/logs/ablation_{args.mode.lower()}.json", result)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
