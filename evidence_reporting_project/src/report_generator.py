from __future__ import annotations

import json

from .data_models import DayRecord, GeneratedReport, RetrievedCard
from .io_utils import dump_json, write_text
from .llm_client import DeepSeekLLMClient
from .mock_llm import MockLLM
from .report_utils import extract_sections, parse_json_candidate
from .template_generator import build_template_payload


AUDIT_KEYS = ("do", "sv", "mlss", "mlvss", "reflux_ratio", "cod", "bod", "ss", "tn", "nhn", "tp", "ph")


def _normalize_payload(payload: dict, day_record: DayRecord, mode: str, method: str) -> dict:
    report_metadata = payload.get("report_metadata") or {}
    monitoring_summary = payload.get("monitoring_summary") or payload.get("monitoring") or ""
    diagnostic_analysis = payload.get("diagnostic_analysis") or payload.get("analysis") or ""
    microbiology_settling_evidence = (
        payload.get("microbiology_settling_evidence")
        or payload.get("microbiology_evidence")
        or payload.get("microbiology_and_settling_evidence")
        or payload.get("microbiology_settling_info")
        or ""
    )
    follow_up_actions = (
        payload.get("follow_up_actions")
        or payload.get("followup_actions")
        or payload.get("follow_up")
        or payload.get("recommendations")
        or payload.get("suggestions")
        or []
    )
    limitations = payload.get("limitations") or payload.get("limitation") or payload.get("limitation_notes") or []
    auditable = payload.get("auditable_statements") or {}
    if not isinstance(follow_up_actions, list):
        follow_up_actions = [str(follow_up_actions)]
    if not isinstance(limitations, list):
        limitations = [str(limitations)]

    normalized_audit = {key: auditable.get(key) for key in AUDIT_KEYS}
    for key in AUDIT_KEYS:
        normalized_audit.setdefault(key, None)

    report_metadata.setdefault("date", day_record.date)
    report_metadata.setdefault("mode", mode)
    report_metadata.setdefault("method", method)
    report_metadata.setdefault("predicted_dominant_taxon", None)

    return {
        "report_metadata": report_metadata,
        "monitoring_summary": monitoring_summary,
        "diagnostic_analysis": diagnostic_analysis,
        "microbiology_settling_evidence": microbiology_settling_evidence,
        "follow_up_actions": follow_up_actions,
        "limitations": limitations,
        "auditable_statements": normalized_audit,
    }


def _report_from_payload(
    payload: dict,
    date: str,
    mode: str,
    method: str,
    llm_provider: str,
    prompt_path: str,
    retrieved_cards: list[RetrievedCard],
    report_id_suffix: str = "",
) -> GeneratedReport:
    report_id = f"mode_{mode.lower()}_{date}_{method}{report_id_suffix}_{llm_provider}"
    normalized_metadata = dict(payload["report_metadata"])
    normalized_metadata["date"] = date
    normalized_metadata["mode"] = mode
    normalized_metadata["method"] = method
    return GeneratedReport(
        report_id=report_id,
        date=date,
        mode=mode,
        method=method,
        llm_provider=llm_provider,
        report_metadata=normalized_metadata,
        monitoring_summary=payload["monitoring_summary"],
        diagnostic_analysis=payload["diagnostic_analysis"],
        microbiology_settling_evidence=payload["microbiology_settling_evidence"],
        follow_up_actions=payload["follow_up_actions"],
        limitations=payload["limitations"],
        auditable_statements=payload["auditable_statements"],
        parsed_sections=extract_sections(
            GeneratedReport(
                report_id=report_id,
                date=date,
                mode=mode,
                method=method,
                llm_provider=llm_provider,
                report_metadata=normalized_metadata,
                monitoring_summary=payload["monitoring_summary"],
                diagnostic_analysis=payload["diagnostic_analysis"],
                microbiology_settling_evidence=payload["microbiology_settling_evidence"],
                follow_up_actions=payload["follow_up_actions"],
                limitations=payload["limitations"],
                auditable_statements=payload["auditable_statements"],
            )
        ),
        retrieved_cards=retrieved_cards,
        prompt_path=prompt_path,
    )


def _to_markdown(report: GeneratedReport) -> str:
    lines = [
        f"# Daily Report {report.date}",
        "",
        "## Metadata",
        json.dumps(report.report_metadata, ensure_ascii=False, indent=2),
        "",
        "## Monitoring Summary",
        report.monitoring_summary,
        "",
        "## Diagnostic Analysis",
        report.diagnostic_analysis,
        "",
        "## Microbiology And Settling Evidence",
        report.microbiology_settling_evidence,
        "",
        "## Follow-up Actions",
    ]
    lines.extend(f"- {item}" for item in report.follow_up_actions)
    lines.extend(["", "## Limitations"])
    lines.extend(f"- {item}" for item in report.limitations)
    lines.extend(["", "## Auditable Statements", json.dumps(report.auditable_statements, ensure_ascii=False, indent=2)])
    return "\n".join(lines)


def generate_report(
    prompt: str,
    day_record: DayRecord,
    mode: str,
    method: str,
    llm_provider: str,
    prompt_path: str,
    retrieved_cards: list[RetrievedCard],
    output_prefix: str,
    report_id_suffix: str = "",
) -> GeneratedReport:
    if method == "template":
        payload = build_template_payload(day_record, mode)
        payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
    elif llm_provider == "mock":
        payload_text = MockLLM().generate_from_components(day_record, mode, method, retrieved_cards)
    elif llm_provider == "deepseek":
        payload_text = DeepSeekLLMClient().generate(prompt)
    else:
        raise ValueError(f"Unsupported llm provider: {llm_provider}")

    write_text(f"{output_prefix}_raw_response.txt", payload_text)
    payload = _normalize_payload(parse_json_candidate(payload_text), day_record, mode, method)
    report = _report_from_payload(payload, day_record.date, mode, method, llm_provider, prompt_path, retrieved_cards, report_id_suffix)
    dump_json(f"{output_prefix}_report.json", report.model_dump())
    write_text(f"{output_prefix}_report.md", _to_markdown(report))
    return report
