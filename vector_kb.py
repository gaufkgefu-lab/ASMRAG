from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+")


@dataclass
class Chunk:
    chunk_id: str
    source: str
    title: str
    text: str
    metadata: dict[str, object]


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text)
    return [part.strip() for part in parts if part.strip()]


def chunk_book_text(text: str, source: str, chunk_size: int = 700, overlap: int = 120) -> list[Chunk]:
    paragraphs = split_paragraphs(text)
    chunks: list[Chunk] = []
    current_parts: list[str] = []
    current_len = 0
    recent_heading = source
    chunk_index = 0

    def flush_chunk() -> None:
        nonlocal current_parts, current_len, chunk_index
        if not current_parts:
            return

        chunk_text = "\n\n".join(current_parts).strip()
        if not chunk_text:
            return

        chunks.append(
            Chunk(
                chunk_id=f"{source}#chunk-{chunk_index:04d}",
                source=source,
                title=recent_heading,
                text=chunk_text,
                metadata={
                    "source": source,
                    "title": recent_heading,
                    "chunk_index": chunk_index,
                    "kind": "book_paragraphs",
                },
            )
        )
        chunk_index += 1

        if overlap <= 0:
            current_parts = []
            current_len = 0
            return

        overlap_parts: list[str] = []
        overlap_len = 0
        for part in reversed(current_parts):
            overlap_parts.insert(0, part)
            overlap_len += len(part)
            if overlap_len >= overlap:
                break
        current_parts = overlap_parts
        current_len = sum(len(part) for part in current_parts)

    for paragraph in paragraphs:
        line_count = paragraph.count("\n") + 1
        compact = paragraph.replace("\n", " ").strip()

        if line_count <= 2 and len(compact) <= 30:
            recent_heading = compact

        if current_len and current_len + len(paragraph) > chunk_size:
            flush_chunk()

        current_parts.append(paragraph)
        current_len += len(paragraph)

        if current_len >= chunk_size:
            flush_chunk()

    flush_chunk()
    return chunks


def parse_markdown_table(text: str, source: str) -> list[Chunk]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return []
    if not lines[0].startswith("|"):
        return []

    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows = [line for line in lines[2:] if line.startswith("|")]
    chunks: list[Chunk] = []

    for index, row in enumerate(rows):
        values = [cell.strip() for cell in row.strip("|").split("|")]
        if len(values) != len(header):
            continue

        row_map = dict(zip(header, values))
        title = f"{row_map.get('微生物', '表格行')} - {row_map.get('工况', '').strip() or '未标注工况'}"
        rendered = "\n".join(f"{key}: {value}" for key, value in row_map.items())

        chunks.append(
            Chunk(
                chunk_id=f"{source}#row-{index + 1:03d}",
                source=source,
                title=title,
                text=rendered,
                metadata={
                    "source": source,
                    "title": title,
                    "chunk_index": index,
                    "kind": "markdown_table_row",
                    "row": row_map,
                },
            )
        )

    return chunks


def load_chunks_from_directory(source_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []

    for path in sorted(source_dir.glob("*.txt")):
        raw_text = path.read_text(encoding="utf-8")
        text = normalize_text(raw_text)

        if path.name.lower() == "tupu.txt":
            chunks.extend(parse_markdown_table(text, path.name))
        else:
            chunks.extend(chunk_book_text(text, path.name))

    return chunks


def iter_terms(text: str) -> Iterable[str]:
    normalized = text.lower()
    for match in TOKEN_PATTERN.finditer(normalized):
        token = match.group(0)
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            if len(token) == 1:
                yield token
                continue

            max_n = min(3, len(token))
            for n in range(2, max_n + 1):
                for index in range(len(token) - n + 1):
                    yield token[index : index + n]
            yield token
        else:
            yield token


def compute_tf(text: str) -> Counter[str]:
    counts = Counter(iter_terms(text))
    return Counter({term: count for term, count in counts.items() if count > 0})


def build_index(chunks: list[Chunk]) -> dict[str, object]:
    doc_term_counts: list[Counter[str]] = []
    document_frequency: Counter[str] = Counter()

    for chunk in chunks:
        counts = compute_tf(f"{chunk.title}\n{chunk.text}")
        doc_term_counts.append(counts)
        document_frequency.update(counts.keys())

    total_docs = len(chunks)
    idf = {
        term: math.log((1 + total_docs) / (1 + frequency)) + 1.0
        for term, frequency in document_frequency.items()
    }

    indexed_chunks = []
    for chunk, counts in zip(chunks, doc_term_counts):
        weighted = {term: (1.0 + math.log(freq)) * idf[term] for term, freq in counts.items()}
        norm = math.sqrt(sum(value * value for value in weighted.values())) or 1.0
        indexed_chunks.append(
            {
                "chunk_id": chunk.chunk_id,
                "source": chunk.source,
                "title": chunk.title,
                "text": chunk.text,
                "metadata": chunk.metadata,
                "weights": weighted,
                "norm": norm,
            }
        )

    return {
        "index_type": "sparse_tfidf_char_ngram",
        "version": 1,
        "document_count": total_docs,
        "idf": idf,
        "chunks": indexed_chunks,
    }


def save_index(index: dict[str, object], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index_path


def load_index(index_path: Path) -> dict[str, object]:
    return json.loads(index_path.read_text(encoding="utf-8"))


def search_index(index: dict[str, object], query: str, top_k: int = 5) -> list[dict[str, object]]:
    idf = index["idf"]
    counts = compute_tf(query)
    if not counts:
        return []

    weighted_query = {}
    for term, freq in counts.items():
        if term not in idf:
            continue
        weighted_query[term] = (1.0 + math.log(freq)) * idf[term]

    if not weighted_query:
        return []

    query_norm = math.sqrt(sum(value * value for value in weighted_query.values())) or 1.0
    results = []

    for chunk in index["chunks"]:
        dot = 0.0
        weights = chunk["weights"]
        for term, query_weight in weighted_query.items():
            doc_weight = weights.get(term)
            if doc_weight is not None:
                dot += query_weight * doc_weight

        if dot <= 0:
            continue

        score = dot / (query_norm * chunk["norm"])
        snippet = f"{chunk['title']}\n{chunk['text'][:2000]}".lower()
        longest_match = SequenceMatcher(None, query.lower(), snippet, autojunk=False).find_longest_match()
        if longest_match.size >= 2:
            score += 0.2 * (longest_match.size / max(len(query), 1))
        results.append(
            {
                "score": score,
                "chunk_id": chunk["chunk_id"],
                "source": chunk["source"],
                "title": chunk["title"],
                "text": chunk["text"],
                "metadata": chunk["metadata"],
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


def build_command(args: argparse.Namespace) -> None:
    source_dir = Path(args.source).resolve()
    output_dir = Path(args.output).resolve()

    chunks = load_chunks_from_directory(source_dir)
    index = build_index(chunks)
    index_path = save_index(index, output_dir)

    summary = {
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "index_path": str(index_path),
        "document_count": index["document_count"],
        "source_files": sorted({chunk.source for chunk in chunks}),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


def search_command(args: argparse.Namespace) -> None:
    index = load_index(Path(args.index).resolve())
    results = search_index(index, args.query, top_k=args.top_k)
    print(json.dumps(results, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and search a local vector knowledge base.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser_ = subparsers.add_parser("build", help="Build an index from a directory.")
    build_parser_.add_argument("--source", required=True, help="Source directory containing .txt files.")
    build_parser_.add_argument("--output", required=True, help="Output directory for the built index.")
    build_parser_.set_defaults(func=build_command)

    search_parser_ = subparsers.add_parser("search", help="Search an existing index.")
    search_parser_.add_argument("--index", required=True, help="Path to index.json.")
    search_parser_.add_argument("--query", required=True, help="Query text.")
    search_parser_.add_argument("--top-k", type=int, default=5, help="Number of results to return.")
    search_parser_.set_defaults(func=search_command)

    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
