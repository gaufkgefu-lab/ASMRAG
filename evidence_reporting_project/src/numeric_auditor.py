from __future__ import annotations

import re

from .data_models import AuditResult, AuditStatementResult, GeneratedReport
from .io_utils import dump_json, load_yaml_like


def audit_report(report: GeneratedReport, reference_table: dict[str, float | None], output_path: str | None = None) -> AuditResult:
    tolerance_cfg = load_yaml_like("configs/audit_tolerance.yaml")
    default_tol = tolerance_cfg.get("default_abs_tolerance", 0.01)
    statement_results = []
    audit_logs = []

    for variable, reported in report.auditable_statements.items():
        reference = reference_table.get(variable)
        tolerance = tolerance_cfg.get("variables", {}).get(variable, {}).get("abs_tolerance", default_tol)
        if reported is None or reference is None:
            passed = False
            note = "Missing reported or reference value."
        else:
            passed = abs(float(reported) - float(reference)) <= float(tolerance)
            note = "matched" if passed else "outside_tolerance"
        statement_results.append(
            AuditStatementResult(
                variable=variable,
                reported_value=reported,
                reference_value=reference,
                tolerance=float(tolerance),
                passed=passed,
                note=note,
            )
        )
        audit_logs.append(
            f"{variable}: reported={reported} reference={reference} tolerance={tolerance} passed={passed}"
        )

    total = len(statement_results)
    passed_count = sum(1 for item in statement_results if item.passed)
    audit_consistency = (passed_count / total) if total else 0.0
    report_level_pass = all(item.passed for item in statement_results) if statement_results else False

    result = AuditResult(
        report_id=report.report_id,
        audit_consistency=audit_consistency,
        report_level_pass=report_level_pass,
        statement_results=statement_results,
        audit_logs=audit_logs,
    )
    if output_path:
        dump_json(output_path, result.model_dump())
    return result


TEXTUAL_ALIAS_PATTERNS = {
    "do": [r"\bdo\b"],
    "sv": [r"\bsv30\b", r"\bsv\b"],
    "mlss": [r"\bmlss\b"],
    "mlvss": [r"\bmlvss\b"],
    "reflux_ratio": [r"reflux ratio", r"return activated sludge flow", r"return ratio"],
    "cod": [r"\bcod\b"],
    "bod": [r"\bbod\b"],
    "ss": [r"\bss\b"],
    "tn": [r"\btn\b"],
    "nhn": [r"\bnhn\b", r"nh4", r"ammonia"],
    "tp": [r"\btp\b"],
    "ph": [r"\bph\b"],
}

EXPECTED_UNITS = {
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


def _textual_source(report: GeneratedReport) -> str:
    return "\n".join(
        [
            report.monitoring_summary or "",
            report.diagnostic_analysis or "",
            report.microbiology_settling_evidence or "",
            "\n".join(report.follow_up_actions or []),
            "\n".join(report.limitations or []),
        ]
    )


def extract_textual_numeric_statements(report: GeneratedReport) -> list[tuple[str, float, str | None]]:
    text = _textual_source(report)
    results: list[tuple[str, float, str | None]] = []
    seen: set[tuple[str, str, str | None]] = set()
    unit_group = r"(mg/L|mg\/L|mL/L|mL\/L|%|pH)?"
    for variable, aliases in TEXTUAL_ALIAS_PATTERNS.items():
        for alias in aliases:
            pattern = re.compile(
                rf"({alias})\s*(?:value\s*)?(?:is|at|=|of|:)?\s*(-?\d+(?:\.\d+)?)\s*{unit_group}",
                flags=re.IGNORECASE,
            )
            for match in pattern.finditer(text):
                raw_value = match.group(2)
                unit = match.group(3) if match.lastindex and match.lastindex >= 3 else None
                normalized_unit = unit.replace("/", "/") if unit else None
                key = (variable, raw_value, normalized_unit)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    results.append((variable, float(raw_value), normalized_unit))
                except ValueError:
                    continue
    return results


def audit_report_textual(
    report: GeneratedReport,
    reference_table: dict[str, float | None],
    output_path: str | None = None,
) -> AuditResult:
    tolerance_cfg = load_yaml_like("configs/audit_tolerance.yaml")
    default_tol = tolerance_cfg.get("default_abs_tolerance", 0.01)
    extracted = extract_textual_numeric_statements(report)
    statement_results = []
    audit_logs = []

    for variable, reported in extracted:
        reference = reference_table.get(variable)
        tolerance = tolerance_cfg.get("variables", {}).get(variable, {}).get("abs_tolerance", default_tol)
        if reference is None:
            passed = False
            note = "No matching same-day reference value."
        else:
            passed = abs(float(reported) - float(reference)) <= float(tolerance)
            note = "matched" if passed else "outside_tolerance"
        statement_results.append(
            AuditStatementResult(
                variable=variable,
                reported_value=reported,
                reference_value=reference,
                tolerance=float(tolerance),
                passed=passed,
                note=note,
            )
        )
        audit_logs.append(
            f"textual:{variable}: reported={reported} reference={reference} tolerance={tolerance} passed={passed}"
        )

    total = len(statement_results)
    passed_count = sum(1 for item in statement_results if item.passed)
    audit_consistency = (passed_count / total) if total else 0.0
    report_level_pass = all(item.passed for item in statement_results) if statement_results else False
    result = AuditResult(
        report_id=report.report_id,
        audit_consistency=audit_consistency,
        report_level_pass=report_level_pass,
        statement_results=statement_results,
        audit_logs=audit_logs,
    )
    if output_path:
        dump_json(output_path, result.model_dump())
    return result


def audit_report_textual_strict(
    report: GeneratedReport,
    reference_table: dict[str, float | None],
    output_path: str | None = None,
    coverage_required: int = 5,
) -> tuple[AuditResult, dict[str, float | int]]:
    tolerance_cfg = load_yaml_like("configs/audit_tolerance.yaml")
    default_tol = tolerance_cfg.get("default_abs_tolerance", 0.01)
    extracted = extract_textual_numeric_statements(report)
    statement_results = []
    audit_logs = []
    grouped: dict[str, list[AuditStatementResult]] = {}

    for variable, reported, unit in extracted:
        reference = reference_table.get(variable)
        tolerance = tolerance_cfg.get("variables", {}).get(variable, {}).get("abs_tolerance", default_tol)
        expected_unit = EXPECTED_UNITS.get(variable)
        unit_ok = True
        unit_note = "unit_missing"
        if expected_unit == "pH":
            unit_ok = unit in (None, "", "pH")
            unit_note = "unit_ok" if unit_ok else f"unit_mismatch:{unit}"
        elif expected_unit is not None:
            unit_ok = unit in (None, "", expected_unit)
            unit_note = "unit_ok" if unit_ok else f"unit_mismatch:{unit}"
        if reference is None:
            passed = False
            note = "No matching same-day reference value."
        else:
            numeric_ok = abs(float(reported) - float(reference)) <= float(tolerance)
            passed = numeric_ok and unit_ok
            if not numeric_ok:
                note = "outside_tolerance"
            elif not unit_ok:
                note = unit_note
            else:
                note = "matched"
        result = AuditStatementResult(
            variable=variable,
            reported_value=reported,
            reference_value=reference,
            tolerance=float(tolerance),
            passed=passed,
            note=note,
        )
        statement_results.append(result)
        grouped.setdefault(variable, []).append(result)
        audit_logs.append(
            f"strict_textual:{variable}: reported={reported} unit={unit} expected_unit={expected_unit} reference={reference} tolerance={tolerance} passed={passed}"
        )

    variable_level_pass = {}
    for variable, items in grouped.items():
        variable_level_pass[variable] = all(item.passed for item in items)
        if not variable_level_pass[variable]:
            audit_logs.append(f"strict_textual:{variable}: repeated mentions are not fully consistent")

    total = len(statement_results)
    passed_count = sum(1 for item in statement_results if item.passed)
    base_consistency = (passed_count / total) if total else 0.0

    unique_variables_mentioned = len(grouped)
    coverage_rate = unique_variables_mentioned / len(EXPECTED_UNITS)
    coverage_penalty = coverage_rate
    strict_consistency = base_consistency * coverage_penalty
    report_level_pass = all(variable_level_pass.values()) and unique_variables_mentioned >= coverage_required if grouped else False

    audit_logs.append(
        f"strict_textual: base_consistency={base_consistency:.6f}, coverage_rate={coverage_rate:.6f}, coverage_penalty={coverage_penalty:.6f}, strict_consistency={strict_consistency:.6f}"
    )

    result = AuditResult(
        report_id=report.report_id,
        audit_consistency=strict_consistency,
        report_level_pass=report_level_pass,
        statement_results=statement_results,
        audit_logs=audit_logs,
    )
    extras = {
        "base_consistency": base_consistency,
        "coverage_rate": coverage_rate,
        "coverage_penalty": coverage_penalty,
        "unique_variables_mentioned": unique_variables_mentioned,
        "coverage_required": coverage_required,
    }
    if output_path:
        dump_json(output_path, {"audit_result": result.model_dump(), "strict_extras": extras})
    return result, extras
