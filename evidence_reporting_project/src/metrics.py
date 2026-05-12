from __future__ import annotations

from .data_models import AuditResult, GeneratedReport
from .io_utils import load_yaml_like
from .report_utils import report_word_count, section_completeness


def _word_count(text: str) -> int:
    return len([part for part in text.replace("\n", " ").split(" ") if part.strip()])


def compute_report_metrics(reports: list[GeneratedReport], audits: list[AuditResult]) -> dict:
    schema = load_yaml_like("configs/report_schema.yaml")
    required_sections = schema["required_sections"]

    avg_report_length = 0.0
    avg_section_completeness = 0.0
    if reports:
        total_words = 0
        total_completeness = 0.0
        for report in reports:
            total_words += report_word_count(report)
            total_completeness += section_completeness(report, required_sections)
        avg_report_length = total_words / len(reports)
        avg_section_completeness = total_completeness / len(reports)

    audit_consistency = 0.0
    report_level_pass_rate = 0.0
    if audits:
        audit_consistency = sum(item.audit_consistency for item in audits) / len(audits)
        report_level_pass_rate = sum(1 for item in audits if item.report_level_pass) / len(audits)

    return {
        "audit_consistency": audit_consistency,
        "report_level_pass_rate": report_level_pass_rate,
        "avg_report_length": avg_report_length,
        "avg_section_completeness": avg_section_completeness,
    }
