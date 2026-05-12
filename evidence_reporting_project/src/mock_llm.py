from __future__ import annotations

import json

from .data_models import DayRecord, RetrievedCard


class MockLLM:
    def generate_from_components(
        self,
        day_record: DayRecord,
        mode: str,
        method: str,
        retrieved_cards: list[RetrievedCard],
    ) -> str:
        reference = day_record.same_day_primary_evidence["reference_table"]
        bio = day_record.optional_biological_evidence or {}
        limitations = []
        if not bio and mode == "A":
            limitations.append("Microbiology observations were not available in Mode A.")
        if bio:
            dominant_taxon = bio.get("dominant_taxon")
            micro_text = (
                f"Same-day manual microscopy is available. Dominant taxon: {dominant_taxon}."
                if dominant_taxon
                else "Same-day manual microscopy is available but no dominant taxon is clear."
            )
        else:
            micro_text = "No same-day manual microscopy evidence is available."

        if day_record.missing_fields:
            limitations.append("Missing fields: " + ", ".join(day_record.missing_fields))

        retrieved_titles = [card.title for card in retrieved_cards]
        if method == "rag" and retrieved_titles:
            limitations.append("Retrieved knowledge was used as background support only.")

        follow_up = [
            "Keep interpretation conservative and verify against next-day trend review.",
            "Continue routine tracking of DO, NHN, COD, and settling-related indicators.",
        ]
        if mode == "B" and bio:
            follow_up.append("Continue same-day microscopy follow-up and watch for shifts in dominant taxa.")

        report = {
            "report_metadata": {
                "date": day_record.date,
                "mode": mode,
                "method": method,
                "retrieved_card_titles": retrieved_titles,
            },
            "monitoring_summary": (
                f"Same-day monitoring shows DO={reference.get('do')} mg/L, SV30={reference.get('sv')} mL/L, "
                f"MLSS={reference.get('mlss')} mg/L, COD={reference.get('cod')} mg/L, NHN={reference.get('nhn')} mg/L."
            ),
            "diagnostic_analysis": (
                "The report is grounded in same-day primary evidence. "
                "High DO together with acceptable residual ammonia suggests a stable and well-aerated condition, "
                "but interpretation remains conservative and should be checked with trend review."
            ),
            "microbiology_settling_evidence": micro_text,
            "follow_up_actions": follow_up,
            "limitations": limitations,
            "auditable_statements": {
                key: reference.get(key)
                for key in ("do", "sv", "mlss", "mlvss", "reflux_ratio", "cod", "bod", "ss", "tn", "nhn", "tp", "ph")
            },
        }
        return json.dumps(report, ensure_ascii=False, indent=2)
