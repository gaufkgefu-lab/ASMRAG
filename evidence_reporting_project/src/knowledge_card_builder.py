from __future__ import annotations

import re
from pathlib import Path

from .data_models import KnowledgeCard
from .io_utils import resolve_path, write_jsonl


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_length: int = 700, overlap: int = 120) -> list[str]:
    normalized = normalize_text(text)
    if len(normalized) <= chunk_length:
        return [normalized]
    chunks = []
    start = 0
    while start < len(normalized):
        end = start + chunk_length
        chunks.append(normalized[start:end])
        if end >= len(normalized):
            break
        start = max(start + chunk_length - overlap, start + 1)
    return chunks


def infer_trigger_cues(text: str) -> list[str]:
    cue_terms = []
    for term in ["污泥膨胀", "溶解氧", "解体", "高负荷", "稳定", "纤毛虫", "钟虫", "轮虫", "氨氮", "SV30", "MLSS"]:
        if term in text:
            cue_terms.append(term)
    if not cue_terms:
        cue_terms.extend(text[:40].split())
    return cue_terms[:8]


def build_knowledge_cards(input_dir: str, output_path: str) -> list[KnowledgeCard]:
    cards: list[KnowledgeCard] = []
    source_dir = resolve_path(input_dir)
    for path in sorted(source_dir.glob("*")):
        if path.suffix.lower() not in {".txt", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        chunks = chunk_text(text)
        for index, chunk in enumerate(chunks):
            title = f"{path.stem} chunk {index + 1}"
            trigger_cues = infer_trigger_cues(chunk)
            first_sentence = chunk.split("\n", 1)[0][:220]
            remarks = chunk[:180]
            cards.append(
                KnowledgeCard(
                    card_id=f"{path.stem}_{index + 1:04d}",
                    title=title,
                    trigger_cues=trigger_cues,
                    core_statement=first_sentence,
                    remarks=remarks,
                    source=path.name,
                    source_type=path.suffix.lower().lstrip("."),
                    chunk_text=chunk,
                )
            )
    write_jsonl(output_path, [card.model_dump() for card in cards])
    return cards
