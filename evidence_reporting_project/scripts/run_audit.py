from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_models import GeneratedReport
from src.io_utils import load_json
from src.numeric_auditor import audit_report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--reference", default="data/processed/day_record_mode_a_20220603.json")
    args = parser.parse_args()

    report = GeneratedReport(**load_json(args.report))
    day_record = load_json(args.reference)
    result = audit_report(report, day_record["same_day_primary_evidence"]["reference_table"])
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
