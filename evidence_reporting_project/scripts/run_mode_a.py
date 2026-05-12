from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline import run_reporting_pipeline


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="20220603")
    parser.add_argument("--method", default="rag", choices=["direct", "rag"])
    parser.add_argument("--llm-provider", default="mock", choices=["mock", "deepseek"])
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    result = run_reporting_pipeline(args.date, "A", args.method, args.llm_provider, args.top_k)
    print(result["report"].report_id)
    print(result["audit"].audit_consistency)


if __name__ == "__main__":
    main()
