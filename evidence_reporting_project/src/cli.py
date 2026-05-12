from __future__ import annotations

import argparse
import json

from .pipeline import run_ablation, run_reporting_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evidence-grounded daily reporting CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--date", required=True)
    run_parser.add_argument("--mode", required=True, choices=["A", "B", "C"])
    run_parser.add_argument("--method", default="rag", choices=["direct", "rag"])
    run_parser.add_argument("--llm-provider", default="mock", choices=["mock", "deepseek"])
    run_parser.add_argument("--top-k", type=int, default=5)

    ablation_parser = subparsers.add_parser("ablation")
    ablation_parser.add_argument("--dates", required=True)
    ablation_parser.add_argument("--mode", required=True, choices=["A", "B"])
    ablation_parser.add_argument("--llm-provider", default="mock", choices=["mock", "deepseek"])
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run":
        result = run_reporting_pipeline(
            date=args.date,
            mode=args.mode,
            method=args.method,
            llm_provider=args.llm_provider,
            top_k=args.top_k,
        )
        print(json.dumps({"report_id": result["report"].report_id, "audit": result["audit"].model_dump()}, ensure_ascii=False, indent=2))
    elif args.command == "ablation":
        dates = [item.strip() for item in args.dates.split(",") if item.strip()]
        print(json.dumps(run_ablation(dates, args.mode, args.llm_provider), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
