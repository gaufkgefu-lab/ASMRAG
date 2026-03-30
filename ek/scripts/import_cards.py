"""Import knowledge cards from CSV or JSON files."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import init_db
from app.repository import upsert_cards


def load_cards(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict) and "items" in payload:
            payload = payload["items"]
        if not isinstance(payload, list):
            raise ValueError("JSON input must be a list of card objects or an object with an 'items' list.")
        return payload
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    raise ValueError(f"Unsupported input format: {suffix}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import knowledge cards from CSV or JSON.")
    parser.add_argument("input_path", help="Path to CSV or JSON knowledge card file.")
    parser.add_argument(
        "--change-summary",
        default="",
        help="Optional note describing why this import/update was performed.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_path)
    init_db()
    cards = load_cards(input_path)
    result = upsert_cards(cards, change_summary=args.change_summary)
    print(
        "Import complete:",
        {
            "import_batch_id": result.import_batch_id,
            "created": result.created,
            "updated": result.updated,
            "skipped": result.skipped,
        },
    )


if __name__ == "__main__":
    main()
