from __future__ import annotations

from .evidence_builder import build_day_record, load_manual_microscopy_map, load_visual_map, load_water_quality_map
from .data_models import AuditResult, GeneratedReport
from .io_utils import dump_json, ensure_directory, load_json, load_yaml_like
from .knowledge_card_builder import build_knowledge_cards
from .metrics import compute_report_metrics
from .mode_c_interface import run_mode_c
from .numeric_auditor import audit_report
from .prompt_builder import build_prompt
from .query_cue_extractor import extract_query_cues
from .report_generator import generate_report
from .retriever import Retriever, load_cards_from_jsonl


def ensure_knowledge_base(settings: dict) -> None:
    kb_path = settings["paths"]["knowledge_cards"]
    if load_cards_from_jsonl(kb_path):
        return
    build_knowledge_cards(settings["paths"]["knowledge_sources"], kb_path)


def run_reporting_pipeline(
    date: str,
    mode: str,
    method: str = "rag",
    llm_provider: str | None = None,
    top_k: int | None = None,
    reuse_existing: bool = True,
) -> dict:
    if mode.upper() == "C":
        run_mode_c()

    settings = load_yaml_like("configs/settings.yaml")
    llm_provider = llm_provider or settings["default_llm_provider"]
    top_k = top_k or settings["default_top_k"]

    ensure_directory(settings["output_dirs"]["reports"])
    ensure_directory(settings["output_dirs"]["audits"])
    ensure_directory(settings["output_dirs"]["retrieval"])
    ensure_directory(settings["output_dirs"]["logs"])

    ensure_knowledge_base(settings)

    day_record = build_day_record(
        date=date,
        water_quality_map=load_water_quality_map(settings["paths"]["water_quality"]),
        manual_map=load_manual_microscopy_map(settings["paths"]["manual_microscopy"]) if mode.upper() == "B" else {},
        visual_map=load_visual_map(settings["paths"]["image_observations"]),
    )
    dump_json(f"data/processed/day_record_mode_{mode.lower()}_{day_record.date}.json", day_record.model_dump())

    query_cues = extract_query_cues(day_record, settings["process_thresholds"])
    dump_json(f"outputs/logs/query_cues_mode_{mode.lower()}_{day_record.date}.json", query_cues)

    cards = load_cards_from_jsonl(settings["paths"]["knowledge_cards"])
    retrieved_cards = []
    retrieval_log_path = f"outputs/retrieval/mode_{mode.lower()}_{day_record.date}_{method}_top{top_k}.json"
    if method == "rag":
        retrieved_cards = Retriever(cards).retrieve(query_cues["retrieval_text"], top_k=top_k, log_path=retrieval_log_path)
    else:
        dump_json(retrieval_log_path, {"query_text": query_cues["retrieval_text"], "results": []})

    prompt, prompt_path = build_prompt(mode.upper(), method, day_record, retrieved_cards)
    dump_json(
        f"outputs/logs/prompt_mode_{mode.lower()}_{day_record.date}_{method}.json",
        {"prompt_path": prompt_path, "prompt": prompt},
    )

    effective_llm_provider = "template_rule" if method == "template" else llm_provider
    method_suffix = f"_top{top_k}" if method == "rag" else ""
    prefix = f"outputs/reports/mode_{mode.lower()}_{day_record.date}_{method}{method_suffix}_{effective_llm_provider}"
    report_json_path = f"{prefix}_report.json"
    audit_json_path = f"outputs/audits/mode_{mode.lower()}_{day_record.date}_{method}{method_suffix}_{effective_llm_provider}_audit.json"
    if reuse_existing:
        try:
            report = GeneratedReport(**load_json(report_json_path))
            audit = AuditResult(**load_json(audit_json_path))
            return {
                "day_record": day_record,
                "query_cues": query_cues,
                "retrieved_cards": retrieved_cards,
                "report": report,
                "audit": audit,
            }
        except Exception:
            pass
    report = generate_report(
        prompt=prompt,
        day_record=day_record,
        mode=mode.upper(),
        method=method,
        llm_provider=effective_llm_provider,
        prompt_path=prompt_path,
        retrieved_cards=retrieved_cards,
        output_prefix=prefix,
        report_id_suffix=method_suffix,
    )
    audit = audit_report(
        report,
        day_record.same_day_primary_evidence["reference_table"],
        output_path=audit_json_path,
    )
    return {
        "day_record": day_record,
        "query_cues": query_cues,
        "retrieved_cards": retrieved_cards,
        "report": report,
        "audit": audit,
    }


def run_ablation(dates: list[str], mode: str, llm_provider: str = "mock") -> dict:
    reports = []
    audits = []
    rows = []
    settings = load_yaml_like("configs/settings.yaml")
    supported_top_k = settings["supported_top_k"]

    for method in ("template", "direct", "rag"):
        if method == "rag":
            top_ks = supported_top_k
        else:
            top_ks = [None]
        for top_k in top_ks:
            for date in dates:
                result = run_reporting_pipeline(
                    date=date,
                    mode=mode,
                    method=method,
                    llm_provider=llm_provider,
                    top_k=top_k or settings["default_top_k"],
                )
                reports.append(result["report"])
                audits.append(result["audit"])
                rows.append(
                    {
                        "date": date,
                        "mode": mode,
                        "method": method,
                        "top_k": top_k,
                        "audit_consistency": result["audit"].audit_consistency,
                        "report_level_pass": result["audit"].report_level_pass,
                    }
                )
    summary = compute_report_metrics(reports, audits)
    return {"rows": rows, "summary": summary}
