from __future__ import annotations

import re
from typing import Any

from .data_models import GeneratedReport, ManualMicroscopyRecord


def normalize_taxon_name(name: str | None) -> str | None:
    if not name:
        return None
    normalized = re.sub(r"[_\-\s]+", " ", str(name).strip().lower())
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff ]+", "", normalized)
    return normalized or None


def known_taxa_from_record(record: ManualMicroscopyRecord | dict | None) -> list[str]:
    if record is None:
        return []
    taxa_counts = record.taxa_counts if isinstance(record, ManualMicroscopyRecord) else record.get("taxa_counts", {})
    names = []
    for name, value in taxa_counts.items():
        if value not in (None, 0, 0.0):
            normalized = normalize_taxon_name(name)
            if normalized:
                names.append(normalized)
    return sorted(set(names))


def extract_sections(report: GeneratedReport) -> dict[str, Any]:
    return {
        "report_metadata": report.report_metadata,
        "monitoring_summary": report.monitoring_summary,
        "diagnostic_analysis": report.diagnostic_analysis,
        "microbiology_settling_evidence": report.microbiology_settling_evidence,
        "follow_up_actions": report.follow_up_actions,
        "limitations": report.limitations,
        "auditable_statements": report.auditable_statements,
    }


def report_word_count(report: GeneratedReport) -> int:
    content = " ".join(
        [
            report.monitoring_summary,
            report.diagnostic_analysis,
            report.microbiology_settling_evidence,
            " ".join(report.follow_up_actions),
            " ".join(report.limitations),
        ]
    )
    return len([part for part in content.replace("\n", " ").split(" ") if part.strip()])


def _token_count(text: str) -> int:
    return len([part for part in str(text).replace("\n", " ").split(" ") if part.strip()])


def _count_measurement_mentions(text: str) -> int:
    lowered = str(text).lower()
    markers = ["do", "sv", "mlss", "mlvss", "cod", "bod", "ss", "tn", "nhn", "tp", "ph", "reflux"]
    return sum(1 for marker in markers if marker in lowered)


def _has_microbiology_signal(text: str) -> bool:
    lowered = str(text).lower()
    markers = [
        "microscopy",
        "microbiology",
        "taxa",
        "taxon",
        "supernatant",
        "color",
        "vorticella",
        "aspidisca",
        "rotifer",
        "epistylis",
        "suctorida",
    ]
    return any(marker in lowered for marker in markers)


def section_score(report: GeneratedReport, section: str) -> float:
    value = getattr(report, section)
    if section == "report_metadata":
        if not isinstance(value, dict):
            return 0.0
        required = ["date", "mode", "method"]
        return 1.0 if all(value.get(key) not in (None, "") for key in required) else 0.0

    if section == "monitoring_summary":
        if not isinstance(value, str):
            return 0.0
        return 1.0 if _token_count(value) >= 20 and _count_measurement_mentions(value) >= 5 else 0.0

    if section == "diagnostic_analysis":
        if not isinstance(value, str):
            return 0.0
        lowered = value.lower()
        interpretive_markers = ["suggest", "indicat", "based on", "consistent", "review", "stable", "condition"]
        return 1.0 if _token_count(value) >= 24 and any(marker in lowered for marker in interpretive_markers) else 0.0

    if section == "microbiology_settling_evidence":
        if not isinstance(value, str):
            return 0.0
        if report.mode == "A":
            mode_a_markers = ["no", "not available", "limited", "settling", "microscopy"]
            return 1.0 if _token_count(value) >= 10 and any(marker in value.lower() for marker in mode_a_markers) else 0.0
        return 1.0 if _token_count(value) >= 16 and _has_microbiology_signal(value) else 0.0

    if section == "follow_up_actions":
        if not isinstance(value, list):
            return 0.0
        non_empty = [item for item in value if str(item).strip()]
        total_tokens = sum(_token_count(str(item)) for item in non_empty)
        return 1.0 if len(non_empty) >= 2 and total_tokens >= 12 else 0.0

    if section == "limitations":
        if not isinstance(value, list):
            return 0.0
        non_empty = [item for item in value if str(item).strip()]
        total_tokens = sum(_token_count(str(item)) for item in non_empty)
        return 1.0 if len(non_empty) >= 2 and total_tokens >= 10 else 0.0

    if section == "auditable_statements":
        if not isinstance(value, dict):
            return 0.0
        non_null = sum(1 for item in value.values() if item is not None)
        return 1.0 if non_null >= 8 else 0.0

    return 1.0 if value not in ("", None, [], {}) else 0.0


def section_completeness(report: GeneratedReport, required_sections: list[str]) -> float:
    total_score = sum(section_score(report, section) for section in required_sections)
    return total_score / len(required_sections)


def detect_taxon_fact_mention(report: GeneratedReport, reference_taxa: list[str]) -> tuple[bool, list[str]]:
    text = " ".join(
        [
            report.monitoring_summary,
            report.diagnostic_analysis,
            report.microbiology_settling_evidence,
            " ".join(report.follow_up_actions),
        ]
    ).lower()
    found = []
    for taxon in reference_taxa:
        if taxon and taxon in text:
            found.append(taxon)
    return (len(found) > 0, sorted(set(found)))


def true_dominant_taxon(record: ManualMicroscopyRecord | dict | None) -> tuple[str | None, str]:
    if record is None:
        return None, "missing_record"
    taxa_counts = record.taxa_counts if isinstance(record, ManualMicroscopyRecord) else record.get("taxa_counts", {})
    normalized_pairs = []
    for name, value in taxa_counts.items():
        if value not in (None, 0, 0.0):
            normalized = normalize_taxon_name(name)
            if normalized:
                normalized_pairs.append((normalized, float(value)))
    if not normalized_pairs:
        return None, "no_positive_taxa"
    normalized_pairs.sort(key=lambda item: item[1], reverse=True)
    top_value = normalized_pairs[0][1]
    top_names = sorted({name for name, value in normalized_pairs if value == top_value})
    if len(top_names) > 1:
        return None, "tie_for_top_count"
    return top_names[0], "ok"


def predicted_dominant_taxon(report: GeneratedReport) -> str | None:
    value = report.report_metadata.get("predicted_dominant_taxon")
    return normalize_taxon_name(value)


def parse_json_candidate(text: str) -> dict[str, Any]:
    import json

    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.startswith("json"):
            candidate = candidate[4:].strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(candidate[start : end + 1])
        raise
