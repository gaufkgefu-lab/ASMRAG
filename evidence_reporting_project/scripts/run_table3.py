from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.experiment_runner import run_experiment_1


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--llm-provider", default="deepseek", choices=["deepseek", "mock"])
    parser.add_argument("--max-workers", type=int, default=6)
    args = parser.parse_args()
    result = run_experiment_1(args.llm_provider, args.max_workers)
    print(json.dumps(result["table3_rows"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
