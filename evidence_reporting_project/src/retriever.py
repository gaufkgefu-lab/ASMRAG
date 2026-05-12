from __future__ import annotations

import math
from collections import Counter

from .data_models import KnowledgeCard, RetrievedCard
from .io_utils import dump_json, read_jsonl


def _simple_tokenize(text: str) -> list[str]:
    lowered = text.lower()
    tokens = []
    current = []
    for ch in lowered:
        if ch.isalnum() or "\u4e00" <= ch <= "\u9fff":
            current.append(ch)
        else:
            if current:
                token = "".join(current)
                tokens.append(token)
                if len(token) > 1 and all("\u4e00" <= c <= "\u9fff" for c in token):
                    for n in (2, 3):
                        for idx in range(len(token) - n + 1):
                            tokens.append(token[idx : idx + n])
                current = []
    if current:
        token = "".join(current)
        tokens.append(token)
    return tokens


class Retriever:
    def __init__(self, cards: list[KnowledgeCard]):
        self.cards = cards
        self.backend = "fallback"
        self.vectorizer = None
        self.matrix = None
        self.card_texts = [
            " ".join(card.trigger_cues) + "\n" + card.title + "\n" + card.core_statement + "\n" + card.chunk_text
            for card in cards
        ]
        self._build_index()

    def _build_index(self) -> None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
            from sklearn.metrics.pairwise import cosine_similarity  # noqa: F401

            self.backend = "sklearn"
            self.vectorizer = TfidfVectorizer()
            self.matrix = self.vectorizer.fit_transform(self.card_texts)
        except Exception:
            self.backend = "fallback"
            self.df = Counter()
            self.doc_vectors = []
            for text in self.card_texts:
                counts = Counter(_simple_tokenize(text))
                self.doc_vectors.append(counts)
                self.df.update(counts.keys())
            self.total_docs = max(len(self.doc_vectors), 1)

    def _fallback_scores(self, query_text: str) -> list[float]:
        query_counts = Counter(_simple_tokenize(query_text))
        query_weights = {}
        for term, freq in query_counts.items():
            idf = math.log((1 + self.total_docs) / (1 + self.df.get(term, 0))) + 1.0
            query_weights[term] = (1.0 + math.log(freq)) * idf
        query_norm = math.sqrt(sum(v * v for v in query_weights.values())) or 1.0
        scores = []
        for counts in self.doc_vectors:
            dot = 0.0
            doc_weights = {}
            for term, freq in counts.items():
                idf = math.log((1 + self.total_docs) / (1 + self.df.get(term, 0))) + 1.0
                doc_weights[term] = (1.0 + math.log(freq)) * idf
            doc_norm = math.sqrt(sum(v * v for v in doc_weights.values())) or 1.0
            for term, query_weight in query_weights.items():
                dot += query_weight * doc_weights.get(term, 0.0)
            scores.append(dot / (query_norm * doc_norm) if dot > 0 else 0.0)
        return scores

    def retrieve(self, query_text: str, top_k: int = 5, log_path: str | None = None) -> list[RetrievedCard]:
        if self.backend == "sklearn":
            from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

            query_vector = self.vectorizer.transform([query_text])
            scores = cosine_similarity(query_vector, self.matrix)[0].tolist()
        else:
            scores = self._fallback_scores(query_text)

        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:top_k]
        retrieved = []
        retrieval_log = {"query_text": query_text, "backend": self.backend, "top_k": top_k, "results": []}
        for rank, (index, score) in enumerate(ranked, start=1):
            card = self.cards[index]
            result = RetrievedCard(
                card_id=card.card_id,
                title=card.title,
                score=float(score),
                rank=rank,
                source=card.source,
                source_type=card.source_type,
                core_statement=card.core_statement,
                remarks=card.remarks,
            )
            retrieval_log["results"].append(result.model_dump())
            retrieved.append(result)

        if log_path:
            dump_json(log_path, retrieval_log)
        return retrieved


def load_cards_from_jsonl(path: str) -> list[KnowledgeCard]:
    return [KnowledgeCard(**item) for item in read_jsonl(path)]
