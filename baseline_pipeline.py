"""Minimal direct-prompt baseline for activated sludge daily report generation."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List

from prompts import DIRECT_BASELINE_PROMPT

PROJECT_DIR = Path(__file__).resolve().parent


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def get_row_by_date(rows: List[Dict[str, str]], target_date: str) -> Dict[str, str]:
    for row in rows:
        if row.get("date") == target_date:
            return row
    raise ValueError(f"No row found for date={target_date}")


def get_microscopy_rows(rows: List[Dict[str, str]], target_date: str) -> List[Dict[str, str]]:
    return [row for row in rows if row.get("date") == target_date]


def format_daily_record(row: Dict[str, str]) -> str:
    return json.dumps(row, ensure_ascii=False, indent=2)


def format_microscopy_rows(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return "No same-day microscopy observations provided."
    return json.dumps(rows, ensure_ascii=False, indent=2)


def build_prompt(daily_record: Dict[str, str], microscopy_rows: List[Dict[str, str]]) -> str:
    return DIRECT_BASELINE_PROMPT.format(
        daily_record=format_daily_record(daily_record),
        microscopy_record=format_microscopy_rows(microscopy_rows),
    )


def call_llm(prompt: str) -> str:
    """
    Placeholder for the real model/API call.

    TODO: replace with your actual LLM client.
    TODO: insert YOUR_MODEL_NAME and YOUR_API_KEY handling here.
    TODO: add retry, timeout, and logging logic for real experiments.
    """
    return (
        "[PLACEHOLDER OUTPUT]\n"
        "Replace call_llm() with a real API or local model call.\n\n"
        "Prompt preview:\n"
        f"{prompt[:1200]}\n"
    )


def save_output(output_dir: Path, target_date: str, payload: Dict[str, object]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"baseline_report_{target_date}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return output_path


def run_pipeline(
    daily_records_path: Path,
    target_date: str,
    microscopy_path: Path | None,
    output_dir: Path,
) -> Path:
    daily_rows = read_csv_rows(daily_records_path)
    daily_record = get_row_by_date(daily_rows, target_date)

    microscopy_rows: List[Dict[str, str]] = []
    if microscopy_path is not None and microscopy_path.exists():
        microscopy_rows = get_microscopy_rows(read_csv_rows(microscopy_path), target_date)

    prompt = build_prompt(daily_record, microscopy_rows)
    llm_output = call_llm(prompt)

    payload = {
        "mode": "direct_llm_baseline",
        "date": target_date,
        "input_daily_record": daily_record,
        "input_microscopy": microscopy_rows,
        "prompt": prompt,
        "report_text": llm_output,
        "assumptions": [
            "This prototype uses example/demo CSV files unless replaced.",
            "No real model call is executed until call_llm() is implemented.",
        ],
    }
    return save_output(output_dir, target_date, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Minimal direct LLM baseline for activated sludge daily reporting."
    )
    parser.add_argument(
        "--daily-records",
        default="daily_records_example.csv",
        help="Path to daily records CSV. TODO: replace with real plant data.",
    )
    parser.add_argument(
        "--microscopy",
        default="microscopy_example.csv",
        help="Optional path to microscopy CSV.",
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Target reporting date, for example 2022-07-14.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for saved JSON outputs.",
    )
    return parser.parse_args()


def resolve_input_path(path_str: str | None) -> Path | None:
    if not path_str:
        return None
    candidate = Path(path_str)
    if candidate.is_absolute():
        return candidate
    return PROJECT_DIR / candidate


def main() -> None:
    args = parse_args()
    microscopy_path = resolve_input_path(args.microscopy)
    output_path = run_pipeline(
        daily_records_path=resolve_input_path(args.daily_records),
        target_date=args.date,
        microscopy_path=microscopy_path,
        output_dir=resolve_input_path(args.output_dir),
    )
    print(f"Saved baseline output to: {output_path}")


if __name__ == "__main__":
    main()
