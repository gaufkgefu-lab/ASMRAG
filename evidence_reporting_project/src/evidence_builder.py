from __future__ import annotations

from typing import Any

from .data_models import DayRecord, ImageDerivedObservation, ManualMicroscopyRecord, WaterQualityRecord
from .io_utils import dump_json, read_csv_records
from .preprocess import keep_missing_fields, normalize_date, to_float_or_none


UNITS = {
    "do": "mg/L",
    "sv": "mL/L",
    "mlss": "mg/L",
    "mlvss": "mg/L",
    "reflux_ratio": "%",
    "cod": "mg/L",
    "bod": "mg/L",
    "ss": "mg/L",
    "tn": "mg/L",
    "nhn": "mg/L",
    "tp": "mg/L",
    "ph": "pH",
}


def load_water_quality_map(path: str) -> dict[str, WaterQualityRecord]:
    records = read_csv_records(path)
    by_date: dict[str, WaterQualityRecord] = {}
    for row in records:
        normalized = normalize_date(row["date"])
        cleaned, missing = keep_missing_fields(row)
        measurements = {k: cleaned.get(k) for k in cleaned if k != "date"}
        by_date[normalized] = WaterQualityRecord(
            date=normalized,
            measurements=measurements,
            units={key: UNITS.get(key, "") for key in measurements},
            missing_fields=missing,
        )
    return by_date


def _dominant_taxon(taxa_counts: dict[str, float | None]) -> str | None:
    available = [(name, value) for name, value in taxa_counts.items() if value not in (None, 0)]
    if not available:
        return None
    available.sort(key=lambda item: item[1], reverse=True)
    return available[0][0]


def load_manual_microscopy_map(path: str) -> dict[str, ManualMicroscopyRecord]:
    records = read_csv_records(path)
    by_date: dict[str, ManualMicroscopyRecord] = {}
    for row in records:
        normalized = normalize_date(row["date"])
        cleaned, missing = keep_missing_fields(row)
        taxa_counts = {
            key: cleaned[key]
            for key in cleaned
            if key not in {"date", "supernatant", "color", "fi", "mlss"} and key is not None
        }
        by_date[normalized] = ManualMicroscopyRecord(
            date=normalized,
            supernatant=str(cleaned.get("supernatant")) if cleaned.get("supernatant") is not None else None,
            color=str(cleaned.get("color")) if cleaned.get("color") is not None else None,
            fi=to_float_or_none(cleaned.get("fi")),
            mlss=to_float_or_none(cleaned.get("mlss")),
            taxa_counts=taxa_counts,
            dominant_taxon=_dominant_taxon(taxa_counts),
            missing_fields=missing,
        )
    return by_date


def load_visual_map(path: str | None) -> dict[str, ImageDerivedObservation]:
    if not path:
        return {}
    try:
        records = read_csv_records(path)
    except FileNotFoundError:
        return {}
    by_date: dict[str, ImageDerivedObservation] = {}
    for row in records:
        normalized = normalize_date(row["date"])
        by_date[normalized] = ImageDerivedObservation(date=normalized)
    return by_date


def build_day_record(
    date: str,
    water_quality_map: dict[str, WaterQualityRecord],
    manual_map: dict[str, ManualMicroscopyRecord] | None = None,
    visual_map: dict[str, ImageDerivedObservation] | None = None,
) -> DayRecord:
    normalized = normalize_date(date)
    water_quality = water_quality_map.get(normalized)
    if water_quality is None:
        raise KeyError(f"No water quality record found for date {normalized}.")

    manual = (manual_map or {}).get(normalized)
    visual = (visual_map or {}).get(normalized)

    same_day_primary = {
        "water_quality": water_quality.model_dump(),
        "reference_table": water_quality.measurements,
    }
    optional_bio = manual.model_dump() if manual else None
    optional_visual = visual.model_dump() if visual else {
        "status": "not_implemented",
        "future_extension": True,
    }

    missing_fields = list(water_quality.missing_fields)
    if manual:
        missing_fields.extend(f"manual_microscopy.{field}" for field in manual.missing_fields)

    return DayRecord(
        date=normalized,
        same_day_primary_evidence=same_day_primary,
        optional_biological_evidence=optional_bio,
        optional_visual_evidence=optional_visual,
        missing_fields=missing_fields,
        mode_hint="B" if manual else "A",
    )


def build_and_save_day_record(
    date: str,
    water_quality_path: str,
    manual_microscopy_path: str | None,
    image_observations_path: str | None,
    output_path: str,
) -> DayRecord:
    day_record = build_day_record(
        date=date,
        water_quality_map=load_water_quality_map(water_quality_path),
        manual_map=load_manual_microscopy_map(manual_microscopy_path) if manual_microscopy_path else {},
        visual_map=load_visual_map(image_observations_path),
    )
    dump_json(output_path, day_record.model_dump())
    return day_record
