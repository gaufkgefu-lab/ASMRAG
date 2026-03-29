"""Minimal RAG pipeline for activated sludge daily report generation."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from prompts import RAG_PROMPT


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_\-\.]+")
PROJECT_DIR = Path(__file__).resolve().parent


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def get_row_by_date(rows: List[Dict[str, str]], target_date: str) -> Dict[str, str]:
    for row in rows:
        if row.get("date") == target_date:
            return row
    raise ValueError(f"No row found for date={target_date}")


def get_microscopy_rows(rows: List[Dict[str, str]], target_date: str) -> List[Dict[str, str]]:
    return [row for row in rows if row.get("date") == target_date]


def tokenize(text: str) -> List[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def row_to_query_text(daily_record: Dict[str, str], microscopy_rows: List[Dict[str, str]]) -> str:
    pieces = [
        f"DO {daily_record.get('DO', '')}",
        f"MLSS {daily_record.get('MLSS', '')}",
        f"SV30 {daily_record.get('SV30', '')}",
        f"SVI {daily_record.get('SVI', '')}",
        f"COD_in {daily_record.get('COD_in', '')}",
        f"COD_out {daily_record.get('COD_out', '')}",
        f"NH4_N_out {daily_record.get('NH4_N_out', '')}",
        daily_record.get("notes", ""),
    ]
    for row in microscopy_rows:
        pieces.extend([row.get("taxon", ""), row.get("abundance", ""), row.get("note", "")])
    return " ".join(piece for piece in pieces if piece)


def build_card_text(card: Dict[str, str]) -> str:
    return " ".join(
        [
            card.get("title", ""),
            card.get("trigger_cues", ""),
            card.get("core_statement", ""),
            card.get("caution", ""),
            card.get("source", ""),
        ]
    )


def compute_idf(docs: List[List[str]]) -> Dict[str, float]:
    total_docs = len(docs)
    df = Counter()
    for doc in docs:
        df.update(set(doc))
    return {
        term: math.log((1 + total_docs) / (1 + count)) + 1.0
        for term, count in df.items()
    }


def tfidf_score(query_tokens: List[str], doc_tokens: List[str], idf: Dict[str, float]) -> float:
    query_counts = Counter(query_tokens)
    doc_counts = Counter(doc_tokens)
    score = 0.0
    for term, q_count in query_counts.items():
        if term in doc_counts:
            score += q_count * doc_counts[term] * idf.get(term, 1.0)
    return score


def keyword_overlap_score(query_tokens: Iterable[str], doc_tokens: Iterable[str]) -> int:
    return len(set(query_tokens).intersection(set(doc_tokens)))


def retrieve_cards(
    query_text: str,
    knowledge_cards: List[Dict[str, str]],
    top_k: int = 3,
) -> List[Dict[str, object]]:
    query_tokens = tokenize(query_text)
    card_tokens = [tokenize(build_card_text(card)) for card in knowledge_cards]
    idf = compute_idf(card_tokens)

    ranked: List[Tuple[float, int, Dict[str, str]]] = []
    for card, tokens in zip(knowledge_cards, card_tokens):
        score = tfidf_score(query_tokens, tokens, idf)
        if score == 0.0:
            score = float(keyword_overlap_score(query_tokens, tokens))
        ranked.append((score, keyword_overlap_score(query_tokens, tokens), card))

    ranked.sort(key=lambda item: (item[0], item[1], item[2].get("id", "")), reverse=True)
    selected = [item for item in ranked if item[0] > 0][:top_k]

    if not selected:
        selected = ranked[: min(top_k, len(ranked))]

    return [
        {
            "retrieval_score": round(score, 4),
            "keyword_overlap": overlap,
            "card": card,
        }
        for score, overlap, card in selected
    ]


def format_daily_record(row: Dict[str, str]) -> str:
    return json.dumps(row, ensure_ascii=False, indent=2)


def format_microscopy_rows(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return "No same-day microscopy observations provided."
    return json.dumps(rows, ensure_ascii=False, indent=2)


def format_retrieved_evidence(retrieved_cards: List[Dict[str, object]]) -> str:
    lines: List[str] = []
    for item in retrieved_cards:
        card = item["card"]
        lines.append(
            json.dumps(
                {
                    "id": card.get("id"),
                    "title": card.get("title"),
                    "trigger_cues": card.get("trigger_cues"),
                    "core_statement": card.get("core_statement"),
                    "caution": card.get("caution"),
                    "source": card.get("source"),
                    "retrieval_score": item.get("retrieval_score"),
                    "keyword_overlap": item.get("keyword_overlap"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return "\n\n".join(lines) if lines else "No knowledge cards retrieved."


def build_prompt(
    daily_record: Dict[str, str],
    microscopy_rows: List[Dict[str, str]],
    retrieved_cards: List[Dict[str, object]],
) -> str:
    return RAG_PROMPT.format(
        daily_record=format_daily_record(daily_record),
        microscopy_record=format_microscopy_rows(microscopy_rows),
        retrieved_evidence=format_retrieved_evidence(retrieved_cards),
    )


def call_llm(prompt: str) -> str:
    """
    Placeholder for the real model/API call.

    TODO: replace with your actual LLM client.
    TODO: insert YOUR_MODEL_NAME and YOUR_API_KEY handling here.
    TODO: keep generation settings fixed across baseline and RAG for fair comparison.
    """
    return (
        "[PLACEHOLDER OUTPUT]\n"
        "Replace call_llm() with a real API or local model call.\n\n"
        "Prompt preview:\n"
        f"{prompt[:1200]}\n"
    )


def save_output(output_dir: Path, target_date: str, payload: Dict[str, object]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"rag_report_{target_date}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return output_path


def run_pipeline(
    daily_records_path: Path,
    microscopy_path: Path,
    knowledge_cards_path: Path,
    target_date: str,
    output_dir: Path,
    top_k: int = 3,
) -> Path:
    daily_rows = read_csv_rows(daily_records_path)
    knowledge_cards = read_csv_rows(knowledge_cards_path)
    microscopy_rows_all = read_csv_rows(microscopy_path) if microscopy_path.exists() else []

    daily_record = get_row_by_date(daily_rows, target_date)
    microscopy_rows = get_microscopy_rows(microscopy_rows_all, target_date)

    query_text = row_to_query_text(daily_record, microscopy_rows)
    retrieved_cards = retrieve_cards(query_text, knowledge_cards, top_k=top_k)
    prompt = build_prompt(daily_record, microscopy_rows, retrieved_cards)
    llm_output = call_llm(prompt)

    payload = {
        "mode": "llm_plus_rag",
        "date": target_date,
        "input_daily_record": daily_record,
        "input_microscopy": microscopy_rows,
        "retrieval_query_text": query_text,
        "retrieved_cards": retrieved_cards,
        "prompt": prompt,
        "report_text": llm_output,
        "retrieval_method": "TF-IDF with keyword-overlap fallback; no embedding model required.",
        "assumptions": [
            "This prototype uses example/demo CSV files unless replaced.",
            "Knowledge cards are simplified engineering placeholders, not formal citations.",
            "No real model call is executed until call_llm() is implemented.",
        ],
    }
    return save_output(output_dir, target_date, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Minimal RAG pipeline for activated sludge daily reporting."
    )
    parser.add_argument(
        "--daily-records",
        default="daily_records_example.csv",
        help="Path to daily records CSV. TODO: replace with real plant data.",
    )
    parser.add_argument(
        "--microscopy",
        default="microscopy_example.csv",
        help="Path to microscopy CSV.",
    )
    parser.add_argument(
        "--knowledge-cards",
        default="knowledge_cards_example.csv",
        help="Path to knowledge card CSV.",
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Target reporting date, for example 2022-07-14.",
    )
    parser.add_argument(
        "--top-k",
        default=3,
        type=int,
        help="Number of retrieved knowledge cards.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for saved JSON outputs.",
    )
    return parser.parse_args()


def resolve_input_path(path_str: str) -> Path:
    candidate = Path(path_str)
    if candidate.is_absolute():
        return candidate
    return PROJECT_DIR / candidate


def main() -> None:
    args = parse_args()
    output_path = run_pipeline(
        daily_records_path=resolve_input_path(args.daily_records),
        microscopy_path=resolve_input_path(args.microscopy),
        knowledge_cards_path=resolve_input_path(args.knowledge_cards),
        target_date=args.date,
        output_dir=resolve_input_path(args.output_dir),
        top_k=args.top_k,
    )
    print(f"Saved RAG output to: {output_path}")


if __name__ == "__main__":
    main()
