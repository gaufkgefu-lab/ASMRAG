from __future__ import annotations

from .data_models import DayRecord
from .report_utils import normalize_taxon_name, true_dominant_taxon


def build_template_payload(day_record: DayRecord, mode: str) -> dict:
    reference = day_record.same_day_primary_evidence["reference_table"]
    bio = day_record.optional_biological_evidence or {}
    dominant_taxon, dominant_status = true_dominant_taxon(bio if bio else None)

    report_metadata = {
        "date": day_record.date,
        "mode": mode,
        "method": "template",
        "predicted_dominant_taxon": dominant_taxon if mode == "B" else None,
        "dominant_taxon_status": dominant_status if mode == "B" else "not_applicable",
    }
    monitoring_summary = (
        f"Date {day_record.date}. DO={reference.get('do')} mg/L; SV30={reference.get('sv')} mL/L; "
        f"MLSS={reference.get('mlss')} mg/L; COD={reference.get('cod')} mg/L; NHN={reference.get('nhn')} mg/L; "
        f"TN={reference.get('tn')} mg/L; TP={reference.get('tp')} mg/L; pH={reference.get('ph')}."
    )
    diagnostic_analysis = (
        "Template baseline summary from same-day evidence only. "
        "This baseline preserves fixed report structure and basic operational interpretation without retrieval-grounded expansion."
    )
    if mode == "B" and bio:
        evidence_parts = []
        if dominant_taxon:
            evidence_parts.append(f"Same-day manual microscopy dominant taxon: {dominant_taxon}.")
        positive_taxa = [
            f"{normalize_taxon_name(name)}={value:g}"
            for name, value in bio.get("taxa_counts", {}).items()
            if value not in (None, 0, 0.0) and normalize_taxon_name(name)
        ][:5]
        if positive_taxa:
            evidence_parts.append("Observed positive taxa: " + ", ".join(positive_taxa) + ".")
        microbiology_settling_evidence = " ".join(evidence_parts) or "Manual microscopy is available but no positive taxon counts are present."
    else:
        microbiology_settling_evidence = "No same-day manual microscopy evidence is used in this template report."

    follow_up_actions = [
        "Review same-day process indicators together with recent trends before changing aeration or recycle settings.",
        "Continue routine monitoring of effluent quality and settling-related indicators.",
    ]
    if mode == "B" and dominant_taxon:
        follow_up_actions.append("Continue routine microscopy and track whether the dominant taxon pattern changes over subsequent days.")

    limitations = ["Template baseline does not use retrieval-grounded background knowledge."]
    if mode == "A":
        limitations.append("Mode A excludes same-day manual microscopy evidence.")
    if day_record.missing_fields:
        limitations.append("Missing fields: " + ", ".join(day_record.missing_fields))

    auditable = {key: reference.get(key) for key in ("do", "sv", "mlss", "mlvss", "reflux_ratio", "cod", "bod", "ss", "tn", "nhn", "tp", "ph")}
    return {
        "report_metadata": report_metadata,
        "monitoring_summary": monitoring_summary,
        "diagnostic_analysis": diagnostic_analysis,
        "microbiology_settling_evidence": microbiology_settling_evidence,
        "follow_up_actions": follow_up_actions,
        "limitations": limitations,
        "auditable_statements": auditable,
    }
