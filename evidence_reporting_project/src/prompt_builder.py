from __future__ import annotations

import json

from .data_models import DayRecord, RetrievedCard
from .io_utils import load_yaml_like, read_text, resolve_path


def _render_template(template_text: str, context: dict[str, str]) -> str:
    try:
        from jinja2 import Template  # type: ignore

        return Template(template_text).render(**context)
    except Exception:
        rendered = template_text
        for key, value in context.items():
            rendered = rendered.replace("{{ " + key + " }}", value)
            rendered = rendered.replace("{{" + key + "}}", value)
        return rendered


def _cards_to_text(cards: list[RetrievedCard]) -> str:
    if not cards:
        return "No retrieved cards."
    lines = []
    for card in cards:
        lines.append(
            f"[rank={card.rank} score={card.score:.4f}] {card.title} | {card.core_statement} | source={card.source}"
        )
    return "\n".join(lines)


def build_prompt(
    mode: str,
    method: str,
    day_record: DayRecord,
    retrieved_cards: list[RetrievedCard] | None = None,
) -> tuple[str, str]:
    prompt_name = f"mode_{mode.lower()}_{'rag' if method == 'rag' else 'direct'}.txt"
    prompt_path = resolve_path(f"prompts/{prompt_name}")
    schema = load_yaml_like("configs/report_schema.yaml")
    context = {
        "report_date": day_record.date,
        "same_day_primary_evidence": json.dumps(day_record.same_day_primary_evidence, ensure_ascii=False, indent=2),
        "optional_biological_evidence": json.dumps(day_record.optional_biological_evidence, ensure_ascii=False, indent=2),
        "retrieved_cards": _cards_to_text(retrieved_cards or []),
        "report_schema": json.dumps(schema, ensure_ascii=False, indent=2),
    }
    return _render_template(read_text(prompt_path), context), str(prompt_path)
