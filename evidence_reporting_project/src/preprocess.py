from __future__ import annotations

from typing import Any


NUMERIC_FIELDS = {
    "do",
    "sv",
    "mlss",
    "mlvss",
    "reflux_ratio",
    "cod",
    "bod",
    "ss",
    "tn",
    "nhn",
    "tp",
    "ph",
    "fi",
}


def normalize_date(value: str) -> str:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits[:8] if len(digits) >= 8 else digits


def to_float_or_none(value: Any) -> float | None:
    if value in (None, "", "NA", "N/A", "nan"):
        return None
    try:
        return float(value)
    except Exception:
        return None


def keep_missing_fields(row: dict[str, Any], numeric_fields: set[str] | None = None) -> tuple[dict[str, Any], list[str]]:
    numeric_fields = numeric_fields or NUMERIC_FIELDS
    cleaned: dict[str, Any] = {}
    missing: list[str] = []
    for key, value in row.items():
        if key in numeric_fields:
            cleaned[key] = to_float_or_none(value)
        else:
            cleaned[key] = value if value not in ("", None) else None
        if cleaned[key] is None:
            missing.append(key)
    return cleaned, missing
