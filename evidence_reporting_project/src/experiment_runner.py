from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from .evidence_builder import load_manual_microscopy_map, load_water_quality_map
from .data_models import AuditResult, GeneratedReport
from .io_utils import dump_json, ensure_directory, load_yaml_like, resolve_path, write_text
from .metrics import compute_report_metrics
from .numeric_auditor import audit_report_textual_strict, extract_textual_numeric_statements
from .pipeline import run_reporting_pipeline
from .report_utils import (
    detect_taxon_fact_mention,
    known_taxa_from_record,
    predicted_dominant_taxon,
    report_word_count,
    section_completeness,
    true_dominant_taxon,
)


@dataclass
class Condition:
    mode: str
    method: str
    top_k: int | None

    @property
    def key(self) -> str:
        if self.method == "rag":
            return f"mode_{self.mode.lower()}__rag__topk_{self.top_k}"
        return f"mode_{self.mode.lower()}__{self.method}"


def _write_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        target.write_text("", encoding="utf-8")
        return
    fieldnames = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _write_minimal_xlsx(path: str | Path, rows: list[dict[str, Any]], sheet_name: str = "Sheet1") -> None:
    from zipfile import ZIP_DEFLATED, ZipFile

    fieldnames = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    def cell_xml(value: Any, row_idx: int, col_idx: int) -> str:
        if value is None:
            return f'<c r="{_cell_ref(row_idx, col_idx)}"/>'
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'<c r="{_cell_ref(row_idx, col_idx)}"><v>{value}</v></c>'
        return f'<c r="{_cell_ref(row_idx, col_idx)}" t="inlineStr"><is><t>{_xml_escape(str(value))}</t></is></c>'

    def _cell_ref(row_idx: int, col_idx: int) -> str:
        letters = ""
        current = col_idx
        while current:
            current, rem = divmod(current - 1, 26)
            letters = chr(65 + rem) + letters
        return f"{letters}{row_idx}"

    sheet_rows = []
    if fieldnames:
        header_xml = "".join(cell_xml(name, 1, index + 1) for index, name in enumerate(fieldnames))
        sheet_rows.append(f'<row r="1">{header_xml}</row>')
        for row_offset, row in enumerate(rows, start=2):
            body_xml = "".join(cell_xml(row.get(name), row_offset, index + 1) for index, name in enumerate(fieldnames))
            sheet_rows.append(f'<row r="{row_offset}">{body_xml}</row>')

    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        "</worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{_xml_escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(target, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", worksheet)


def _all_dates() -> list[str]:
    settings = load_yaml_like("configs/settings.yaml")
    water_map = load_water_quality_map(settings["paths"]["water_quality"])
    return sorted(water_map.keys())


def _paired_manual_dates() -> list[str]:
    settings = load_yaml_like("configs/settings.yaml")
    water_dates = set(load_water_quality_map(settings["paths"]["water_quality"]).keys())
    manual_dates = set(load_manual_microscopy_map(settings["paths"]["manual_microscopy"]).keys())
    return sorted(water_dates & manual_dates)


def _report_body_text(report: GeneratedReport) -> str:
    return "\n".join(
        [
            report.monitoring_summary or "",
            report.diagnostic_analysis or "",
            report.microbiology_settling_evidence or "",
            "\n".join(report.follow_up_actions or []),
            "\n".join(report.limitations or []),
        ]
    )


def _numeric_mentions(report: GeneratedReport) -> list[str]:
    import re

    text = _report_body_text(report)
    values = []
    for match in re.finditer(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?![A-Za-z])", text):
        value = match.group(0)
        # Exclude calendar-like dates from unsupported-claim accounting.
        if len(value) == 8 and value.isdigit():
            continue
        values.append(value)
    return values


def _unsupported_numeric_claim_rate(report: GeneratedReport) -> float:
    numeric_values = _numeric_mentions(report)
    if not numeric_values:
        return 0.0
    bound_values = [f"{value:g}" for _, value, _ in extract_textual_numeric_statements(report)]
    bound_set = set(bound_values)
    unsupported = 0
    for value in numeric_values:
        normalized = f"{float(value):g}"
        if normalized not in bound_set:
            unsupported += 1
    return unsupported / len(numeric_values)


def _retrieval_context_metrics(report: GeneratedReport) -> tuple[float | str, float | str]:
    if not report.retrieved_cards:
        return "--", "--"
    scores = [card.score for card in report.retrieved_cards]
    sources = {card.source for card in report.retrieved_cards}
    return sum(scores) / len(scores), len(sources) / len(report.retrieved_cards)


def _biological_evidence_utilization(report: GeneratedReport, manual_record: Any) -> int:
    body = _report_body_text(report).lower()
    taxa_used, _ = detect_taxon_fact_mention(report, known_taxa_from_record(manual_record))
    biological_terms = ["supernatant", "color", "dominant", "microscopy", "taxa", "taxon", "fi", "mlss"]
    return int(taxa_used or any(term in body for term in biological_terms))


def _unsupported_taxon_claim_rate(report: GeneratedReport, manual_record: Any | None) -> float:
    body = _report_body_text(report).lower()
    # Use the taxonomy columns available in the manual record as the vocabulary.
    taxa_vocab = []
    if manual_record is not None:
        taxa_vocab = [normalize for normalize in known_taxa_from_record({"taxa_counts": manual_record.taxa_counts})]
        all_taxa = [name for name in manual_record.taxa_counts.keys()]
    else:
        all_taxa = []
    if not all_taxa:
        # Fallback to common taxa seen in this dataset.
        all_taxa = [
            "epistylis",
            "scale lnsect",
            "mormon cricket",
            "rotifer",
            "aspidisca",
            "vorticella",
            "arcella",
            "litonotus",
            "chilodonela",
            "suctorida",
            "nematoda",
            "euplotes",
        ]
    mentioned = []
    for name in all_taxa:
        normalized = str(name).replace("_", " ").lower()
        if normalized and normalized in body:
            mentioned.append(normalized)
    if not mentioned:
        return 0.0
    supported = set(taxa_vocab)
    unsupported = [name for name in mentioned if name not in supported]
    return len(unsupported) / len(mentioned)


def _run_condition_date(condition: Condition, date: str, llm_provider: str, top_k: int) -> dict[str, Any]:
    return run_reporting_pipeline(
        date=date,
        mode=condition.mode,
        method=condition.method,
        llm_provider=llm_provider,
        top_k=top_k,
        reuse_existing=True,
    )


def _load_cached_condition_date(condition: Condition, date: str, llm_provider: str) -> dict[str, Any] | None:
    effective_provider = "template_rule" if condition.method == "template" else llm_provider
    method_suffix = f"_top{condition.top_k}" if condition.method == "rag" else ""
    report_path = resolve_path(
        f"outputs/reports/mode_{condition.mode.lower()}_{date}_{condition.method}{method_suffix}_{effective_provider}_report.json"
    )
    audit_path = resolve_path(
        f"outputs/audits/mode_{condition.mode.lower()}_{date}_{condition.method}{method_suffix}_{effective_provider}_audit.json"
    )
    if not report_path.exists() or not audit_path.exists():
        return None
    try:
        report = GeneratedReport(**json.loads(report_path.read_text(encoding="utf-8")))
        audit = AuditResult(**json.loads(audit_path.read_text(encoding="utf-8")))
        return {"report": report, "audit": audit}
    except Exception:
        return None


def run_experiment_1(llm_provider: str = "deepseek", max_workers: int = 6) -> dict[str, Any]:
    settings = load_yaml_like("configs/settings.yaml")
    output_dir = ensure_directory("outputs/exp1_table3")
    dates = _all_dates()
    water_map = load_water_quality_map(settings["paths"]["water_quality"])
    required_sections = load_yaml_like("configs/report_schema.yaml")["required_sections"]
    conditions = [
        Condition("A", "template", None),
        Condition("A", "direct", None),
        Condition("A", "rag", 3),
        Condition("A", "rag", 5),
        Condition("A", "rag", 8),
        Condition("B", "template", None),
        Condition("B", "direct", None),
        Condition("B", "rag", 3),
        Condition("B", "rag", 5),
        Condition("B", "rag", 8),
    ]

    report_level_rows: list[dict[str, Any]] = []
    statement_rows: list[dict[str, Any]] = []
    retrieval_rows: list[dict[str, Any]] = []
    run_config_rows: list[dict[str, Any]] = []
    table3_rows: list[dict[str, Any]] = []

    for condition in conditions:
        reports = []
        audits = []
        condition_textual_consistency = []
        condition_coverage = []
        condition_unsupported_numeric = []
        condition_retrieval_scores = []
        condition_source_diversity = []
        top_k = condition.top_k or settings["default_top_k"]
        cached_results = []
        missing_dates = []
        for date in dates:
            cached = _load_cached_condition_date(condition, date, llm_provider)
            if cached is None:
                missing_dates.append(date)
            else:
                cached_results.append(cached)
        futures = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for date in missing_dates:
                futures.append(executor.submit(_run_condition_date, condition, date, llm_provider, top_k))
            for future in as_completed(futures):
                cached_results.append(future.result())
            for result in cached_results:
                report = result["report"]
                date = report.date
                audit, strict_extras = audit_report_textual_strict(
                    report,
                    water_map[date].measurements,
                    output_path=output_dir / f"{report.report_id}_strict_textual_audit.json",
                )
                retrieval_score, source_diversity = _retrieval_context_metrics(report)
                if retrieval_score != "--":
                    condition_retrieval_scores.append(float(retrieval_score))
                    condition_source_diversity.append(float(source_diversity))
                unsupported_numeric_rate = _unsupported_numeric_claim_rate(report)
                condition_textual_consistency.append(strict_extras["base_consistency"])
                condition_coverage.append(strict_extras["coverage_rate"])
                condition_unsupported_numeric.append(unsupported_numeric_rate)
                reports.append(report)
                audits.append(audit)
                completeness = section_completeness(report, required_sections)
                report_level_rows.append(
                    {
                        "condition_key": condition.key,
                        "date": date,
                        "mode": condition.mode,
                        "method": condition.method,
                        "top_k": condition.top_k,
                        "report_id": report.report_id,
                        "llm_provider": report.llm_provider,
                        "textual_numeric_consistency": strict_extras["base_consistency"],
                        "evidence_coverage": strict_extras["coverage_rate"],
                        "strict_textual_score": audit.audit_consistency,
                        "unsupported_numeric_claim_rate": unsupported_numeric_rate,
                        "report_level_pass": int(audit.report_level_pass),
                        "report_word_count": report_word_count(report),
                        "section_completeness": completeness,
                        "retrieved_card_count": len(report.retrieved_cards),
                        "retrieval_relevance_score": retrieval_score,
                        "source_diversity": source_diversity,
                    }
                )
                for item in audit.statement_results:
                    statement_rows.append(
                        {
                            "condition_key": condition.key,
                            "date": date,
                            "report_id": report.report_id,
                            "variable": item.variable,
                            "reported_value": item.reported_value,
                            "reference_value": item.reference_value,
                            "tolerance": item.tolerance,
                            "passed": int(item.passed),
                            "note": item.note,
                        }
                    )
                retrieval_log_path = resolve_path(f"outputs/retrieval/mode_{condition.mode.lower()}_{date}_{condition.method}_top{top_k}.json")
                if retrieval_log_path.exists():
                    retrieval_log = json.loads(retrieval_log_path.read_text(encoding="utf-8"))
                    for row in retrieval_log.get("results", []):
                        retrieval_rows.append(
                            {
                                "condition_key": condition.key,
                                "date": date,
                                "mode": condition.mode,
                                "method": condition.method,
                                "top_k": condition.top_k,
                                "backend": retrieval_log.get("backend", ""),
                                "query_text": retrieval_log.get("query_text", ""),
                                "rank": row.get("rank"),
                                "card_id": row.get("card_id"),
                                "title": row.get("title"),
                                "score": row.get("score"),
                                "source": row.get("source"),
                                "source_type": row.get("source_type"),
                            }
                        )

        summary = compute_report_metrics(reports, audits)
        mean_retrieval_score = (
            sum(condition_retrieval_scores) / len(condition_retrieval_scores)
            if condition_retrieval_scores
            else "--"
        )
        mean_source_diversity = (
            sum(condition_source_diversity) / len(condition_source_diversity)
            if condition_source_diversity
            else "--"
        )
        table3_rows.append(
            {
                "Mode": f"Mode {condition.mode}",
                "Method": "Template-based reporting" if condition.method == "template" else ("Direct prompting without retrieval" if condition.method == "direct" else "Proposed retrieval-grounded workflow"),
                "Top-k": condition.top_k if condition.top_k is not None else "--",
                "retrieval_relevance_score": round(mean_retrieval_score, 6) if mean_retrieval_score != "--" else "--",
                "source_diversity": round(mean_source_diversity, 6) if mean_source_diversity != "--" else "--",
                "textual_numeric_consistency": round(sum(condition_textual_consistency) / len(condition_textual_consistency), 6),
                "evidence_coverage": round(sum(condition_coverage) / len(condition_coverage), 6),
                "unsupported_numeric_claim_rate": round(sum(condition_unsupported_numeric) / len(condition_unsupported_numeric), 6),
                "report_level_pass_rate": round(summary["report_level_pass_rate"], 6),
                "avg_report_length": round(summary["avg_report_length"], 3),
                "avg_section_completeness": round(summary["avg_section_completeness"], 6),
            }
        )
        run_config_rows.append(
            {
                "condition_key": condition.key,
                "mode": condition.mode,
                "method": condition.method,
                "top_k": condition.top_k,
                "date_count": len(dates),
                "llm_provider": llm_provider if condition.method != "template" else "template_rule",
                "knowledge_card_path": settings["paths"]["knowledge_cards"],
                "paired_subset": "no",
            }
        )

    _write_csv(output_dir / "table3_main.csv", table3_rows)
    _write_minimal_xlsx(output_dir / "table3_main.xlsx", table3_rows, sheet_name="table3_main")
    _write_csv(output_dir / "report_level_metrics.csv", report_level_rows)
    _write_csv(output_dir / "statement_level_audit.csv", statement_rows)
    _write_csv(output_dir / "retrieval_logs.csv", retrieval_rows)
    _write_csv(output_dir / "run_config_summary.csv", run_config_rows)
    sanity = _sanity_checks_exp1(table3_rows)
    write_text(output_dir / "sanity_checks.md", sanity)
    return {
        "table3_rows": table3_rows,
        "report_level_rows": report_level_rows,
        "statement_rows": statement_rows,
        "retrieval_rows": retrieval_rows,
        "run_config_rows": run_config_rows,
    }


def _sanity_checks_exp1(table3_rows: list[dict[str, Any]]) -> str:
    notes = ["# Experiment 1 sanity checks", ""]
    if all(float(row["textual_numeric_consistency"]) == 1.0 for row in table3_rows):
        notes.append("- All textual numeric consistency values are 1.0. Investigate whether the model is copying numeric statements exactly from same-day evidence.")
    if all(float(row["report_level_pass_rate"]) == 1.0 for row in table3_rows):
        notes.append("- All report-level pass rates are 1.0. This likely means auditable statements remained fully table-bounded in the current run.")
    rag_rows = [row for row in table3_rows if row["Method"] == "Proposed retrieval-grounded workflow"]
    if len({(row["Mode"], row["retrieval_relevance_score"], row["textual_numeric_consistency"], row["evidence_coverage"], row["avg_report_length"], row["avg_section_completeness"]) for row in rag_rows}) < len(rag_rows):
        notes.append("- Some RAG Top-k rows are identical. Check whether retrieved card sets or generated outputs collapsed across retrieval depths.")
    if len(notes) == 2:
        notes.append("- No automatic sanity warnings were triggered.")
    return "\n".join(notes)


def run_experiment_2(llm_provider: str = "deepseek", max_workers: int = 6) -> dict[str, Any]:
    settings = load_yaml_like("configs/settings.yaml")
    output_dir = ensure_directory("outputs/exp2_table4")
    dates = _paired_manual_dates()
    manual_map = load_manual_microscopy_map(settings["paths"]["manual_microscopy"])
    water_map = load_water_quality_map(settings["paths"]["water_quality"])

    paired_rows = []
    micro_eval_rows = []
    truth_rows = []
    statement_rows = []
    run_config_rows = []

    result_map: dict[tuple[str, str], dict[str, Any]] = {}
    missing_jobs = []
    for date in dates:
        for mode in ("A", "B"):
            condition = Condition(mode, "rag", 5)
            cached = _load_cached_condition_date(condition, date, llm_provider)
            if cached is None:
                missing_jobs.append((mode, date))
            else:
                result_map[(mode, date)] = cached

    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for mode, date in missing_jobs:
            futures.append((mode, date, executor.submit(run_reporting_pipeline, date, mode, "rag", llm_provider, 5, True)))
        for mode, date, future in futures:
            result_map[(mode, date)] = future.result()

    for date in dates:
        result_a = result_map[("A", date)]
        result_b = result_map[("B", date)]
        manual_record = manual_map[date]
        truth_taxon, truth_status = true_dominant_taxon(manual_record)
        truth_rows.append(
            {
                "date": date,
                "true_dominant_taxon": truth_taxon,
                "truth_status": truth_status,
                "positive_taxa_count": len(known_taxa_from_record(manual_record)),
            }
        )
        for result in (result_a, result_b):
            report = result["report"]
            reference_table = water_map[date].measurements
            audit, strict_extras = audit_report_textual_strict(
                report,
                reference_table,
                output_path=output_dir / f"{report.report_id}_textual_audit.json",
            )
            detected, mentions = detect_taxon_fact_mention(report, known_taxa_from_record(manual_record))
            unsupported_taxon_rate = _unsupported_taxon_claim_rate(report, manual_record if report.mode == "B" else None)
            biological_utilization = _biological_evidence_utilization(report, manual_record) if report.mode == "B" else 0
            predicted_taxon = predicted_dominant_taxon(report)
            dominant_match = int(predicted_taxon == truth_taxon) if truth_status == "ok" and report.mode == "B" else None
            paired_rows.append(
                {
                    "date": date,
                    "mode": report.mode,
                    "report_id": report.report_id,
                    "taxon_fact_mention": int(detected),
                    "mentioned_taxa": ", ".join(mentions),
                    "predicted_dominant_taxon": predicted_taxon,
                    "true_dominant_taxon": truth_taxon,
                    "truth_status": truth_status,
                    "audit_consistency": audit.audit_consistency,
                    "report_level_pass": int(audit.report_level_pass),
                    "base_consistency": strict_extras["base_consistency"],
                    "coverage_rate": strict_extras["coverage_rate"],
                    "coverage_penalty": strict_extras["coverage_penalty"],
                    "unique_variables_mentioned": strict_extras["unique_variables_mentioned"],
                    "unsupported_taxon_claim_rate": unsupported_taxon_rate,
                    "biological_evidence_utilization": biological_utilization,
                }
            )
            micro_eval_rows.append(
                {
                    "date": date,
                    "mode": report.mode,
                    "taxon_fact_mention": int(detected),
                    "predicted_dominant_taxon": predicted_taxon,
                    "true_dominant_taxon": truth_taxon,
                    "truth_status": truth_status,
                    "dominant_taxon_correct": dominant_match,
                    "audit_consistency": audit.audit_consistency,
                    "base_consistency": strict_extras["base_consistency"],
                    "coverage_rate": strict_extras["coverage_rate"],
                    "unsupported_taxon_claim_rate": unsupported_taxon_rate,
                    "biological_evidence_utilization": biological_utilization,
                }
            )
            for item in audit.statement_results:
                statement_rows.append(
                    {
                        "date": date,
                        "mode": report.mode,
                        "report_id": report.report_id,
                        "variable": item.variable,
                        "reported_value": item.reported_value,
                        "reference_value": item.reference_value,
                        "tolerance": item.tolerance,
                        "passed": int(item.passed),
                        "note": item.note,
                        "audit_type": "strict_textual",
                        "base_consistency": strict_extras["base_consistency"],
                        "coverage_rate": strict_extras["coverage_rate"],
                        "coverage_penalty": strict_extras["coverage_penalty"],
                    }
                )

    table4_rows = []
    for mode in ("A", "B"):
        mode_rows = [row for row in paired_rows if row["mode"] == mode]
        eval_rows = [row for row in micro_eval_rows if row["mode"] == mode]
        taxon_fact_mention_rate = sum(row["taxon_fact_mention"] for row in eval_rows) / len(eval_rows)
        total_statements = [row for row in statement_rows if row["mode"] == mode]
        overall_audit_consistency = (
            sum(row["passed"] for row in total_statements) / len(total_statements)
            if total_statements
            else 0.0
        )
        if mode == "B":
            evaluable = [row for row in eval_rows if row["truth_status"] == "ok"]
            valid = [row for row in evaluable if row["dominant_taxon_correct"] is not None]
            dominant_accuracy = (sum(row["dominant_taxon_correct"] for row in valid) / len(valid)) if valid else None
            style = "Biology-informed report content integrated into the same shared schema."
        else:
            dominant_accuracy = None
            style = "Process-focused report content without same-day manual microscopy evidence."
        unsupported_taxon_claim_rate = sum(row["unsupported_taxon_claim_rate"] for row in eval_rows) / len(eval_rows)
        biological_evidence_utilization_rate = sum(row["biological_evidence_utilization"] for row in eval_rows) / len(eval_rows)
        textual_numeric_consistency = sum(row["audit_consistency"] for row in eval_rows) / len(eval_rows)
        table4_rows.append(
            {
                "Mode": f"Mode {mode}",
                "taxon_fact_mention_rate": round(taxon_fact_mention_rate, 6),
                "unsupported_taxon_claim_rate": round(unsupported_taxon_claim_rate, 6),
                "dominant_taxon_accuracy": round(dominant_accuracy, 6) if dominant_accuracy is not None else "N/A",
                "biological_evidence_utilization_rate": round(biological_evidence_utilization_rate, 6),
                "textual_numeric_consistency": round(textual_numeric_consistency, 6),
                "report_content_style": style,
            }
        )
        run_config_rows.append(
            {
                "mode": mode,
                "method": "rag",
                "top_k": 5,
                "date_count": len(mode_rows),
                "paired_subset": "yes",
                "llm_provider": llm_provider,
                "audit_standard": "strict_textual_binding_with_repeat_consistency_and_coverage_penalty",
            }
        )

    _write_csv(output_dir / "table4_main.csv", table4_rows)
    _write_minimal_xlsx(output_dir / "table4_main.xlsx", table4_rows, sheet_name="table4_main")
    _write_csv(output_dir / "microbiology_eval.csv", micro_eval_rows)
    _write_csv(output_dir / "microscopy_truth.csv", truth_rows)
    _write_csv(output_dir / "paired_reports.csv", paired_rows)
    _write_csv(output_dir / "statement_level_audit.csv", statement_rows)
    _write_csv(output_dir / "run_config_summary.csv", run_config_rows)
    write_text(output_dir / "evaluation_rules.md", _evaluation_rules_md())
    write_text(output_dir / "sanity_checks.md", _sanity_checks_exp2(table4_rows, paired_rows))
    return {
        "table4_rows": table4_rows,
        "paired_rows": paired_rows,
        "micro_eval_rows": micro_eval_rows,
        "truth_rows": truth_rows,
    }


def _evaluation_rules_md() -> str:
    return """# Evaluation rules

- Paired subset: all dates that exist in both `Process_variables.csv` and `Manual_microscopy.csv`.
- Same date pool is used for Mode A and Mode B in Experiment 2.
- Overall audit consistency in Experiment 2 uses the strict textual audit standard:
  - extract variable-value-unit triples from report body text
  - bind each triple to a same-day reference variable
  - require numeric match within tolerance
  - require unit compatibility when a unit is explicitly stated
  - if the same variable is mentioned multiple times, all mentions must be mutually consistent
  - apply a coverage penalty equal to the body-text coverage rate over the shared auditable variable set
  - final strict score = base_consistency * coverage_rate
- Unsupported taxon claim rate:
  - Mode A has no same-day microscopy evidence, so any explicit taxon claim is treated as unsupported
  - Mode B supports only taxa with positive same-day manual microscopy counts
  - claims about taxa not present in the positive same-day microscopy set are counted as unsupported
- Biological evidence utilization rate:
  - Mode B report is counted as using biological evidence if it mentions positive-count taxa or explicit microscopy-related evidence fields
  - Mode A is fixed to 0 because manual microscopy evidence is intentionally unavailable
- True dominant taxon:
  - positive-count taxa are considered candidates
  - if no taxon has a positive count, the day is marked `no_positive_taxa`
  - if two or more taxa share the same maximum positive count, the day is marked `tie_for_top_count`
  - dominant-taxon accuracy is evaluated only on rows with `truth_status = ok`
- Taxon normalization:
  - lowercase
  - underscores and repeated whitespace are normalized to spaces
  - non-alphanumeric punctuation is removed
- Predicted dominant taxon:
  - read from `report_metadata.predicted_dominant_taxon`
  - if missing, prediction is treated as missing and counts as incorrect on evaluable Mode B days
- Taxon-fact mention:
  - counted only when a report explicitly contains one or more same-day positive taxon names from the paired manual microscopy record
  - generic biology background statements without same-day taxon mention are not counted
"""


def _sanity_checks_exp2(table4_rows: list[dict[str, Any]], paired_rows: list[dict[str, Any]]) -> str:
    notes = ["# Experiment 2 sanity checks", ""]
    lookup = {row["Mode"]: row for row in table4_rows}
    if lookup.get("Mode B", {}).get("dominant_taxon_accuracy") == 1.0:
        notes.append("- Mode B dominant-taxon accuracy is 1.0. Verify whether the prompt is echoing the manual dominant taxon too directly.")
    if abs(float(lookup["Mode A"]["taxon_fact_mention_rate"]) - float(lookup["Mode B"]["taxon_fact_mention_rate"])) < 1e-9:
        notes.append("- Taxon fact mention rate is identical between Mode A and Mode B, which is unexpected and should be checked.")
    mode_a_dates = {row["date"] for row in paired_rows if row["mode"] == "A"}
    mode_b_dates = {row["date"] for row in paired_rows if row["mode"] == "B"}
    if mode_a_dates != mode_b_dates:
        notes.append("- Mode A and Mode B used different paired date pools.")
    if len(notes) == 2:
        notes.append("- No automatic sanity warnings were triggered.")
    return "\n".join(notes)
