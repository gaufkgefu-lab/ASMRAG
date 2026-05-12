from __future__ import annotations

from .data_models import DayRecord


def extract_query_cues(day_record: DayRecord, thresholds: dict) -> dict:
    primary = day_record.same_day_primary_evidence["reference_table"]
    biological = day_record.optional_biological_evidence or {}

    process_anomalies: list[str] = []
    water_quality_anomalies: list[str] = []
    microbiology_observations: list[str] = []
    settling_signal_placeholders: list[str] = ["settling_state_signal: future_extension_slot"]
    missing_field_prompts: list[str] = [f"missing:{item}" for item in day_record.missing_fields]

    do_value = primary.get("do")
    if do_value is not None and do_value > thresholds.get("high_do", 5.5):
        process_anomalies.append(f"high_do:{do_value}")
    if do_value is not None and do_value < thresholds.get("low_do", 1.5):
        process_anomalies.append(f"low_do:{do_value}")

    sv_value = primary.get("sv")
    if sv_value is not None and sv_value > thresholds.get("high_sv", 35.0):
        process_anomalies.append(f"elevated_sv30:{sv_value}")

    for key in ("cod", "nhn", "tn", "tp"):
        value = primary.get(key)
        threshold_key = f"high_{key}"
        if value is not None and value > thresholds.get(threshold_key, 9999):
            water_quality_anomalies.append(f"high_{key}:{value}")

    if biological:
        dominant_taxon = biological.get("dominant_taxon")
        if dominant_taxon:
            microbiology_observations.append(f"dominant_taxon:{dominant_taxon}")
        taxa_counts = biological.get("taxa_counts", {})
        for name, value in taxa_counts.items():
            if value not in (None, 0, 0.0):
                microbiology_observations.append(f"{name}:{value}")
        if biological.get("supernatant") is not None:
            microbiology_observations.append(f"supernatant:{biological['supernatant']}")
        if biological.get("color") is not None:
            microbiology_observations.append(f"sludge_color:{biological['color']}")

    retrieval_text = " | ".join(
        process_anomalies + water_quality_anomalies + microbiology_observations + settling_signal_placeholders + missing_field_prompts
    )

    return {
        "date": day_record.date,
        "process_anomalies": process_anomalies,
        "water_quality_anomalies": water_quality_anomalies,
        "microbiology_observations": microbiology_observations,
        "settling_signal_placeholders": settling_signal_placeholders,
        "missing_field_prompts": missing_field_prompts,
        "retrieval_text": retrieval_text,
    }
