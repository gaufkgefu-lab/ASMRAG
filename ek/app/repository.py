"""Query and persistence helpers for knowledge cards."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from app.db import get_connection


REQUIRED_FIELDS = [
    "knowledge_id",
    "title",
    "category",
    "trigger_cues",
    "core_statement",
    "optional_notes",
    "source_type",
    "source_title",
    "source_author",
    "source_year",
    "source_link",
    "tags",
    "version",
    "created_at",
    "updated_at",
    "status",
]


@dataclass
class ImportResult:
    import_batch_id: str
    created: int
    updated: int
    skipped: int


def _normalize_list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            loaded = json.loads(text)
            if isinstance(loaded, list):
                return [str(item).strip() for item in loaded if str(item).strip()]
        except json.JSONDecodeError:
            pass
    parts = [part.strip() for part in text.replace("|", ";").split(";")]
    return [part for part in parts if part]


def normalize_card(raw_card: dict[str, Any]) -> dict[str, Any]:
    card: dict[str, Any] = {}
    missing = [field for field in REQUIRED_FIELDS if field not in raw_card]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    for field in REQUIRED_FIELDS:
        if field in {"trigger_cues", "tags"}:
            card[field] = _normalize_list_field(raw_card.get(field))
        elif field == "source_year":
            value = raw_card.get(field)
            card[field] = int(value) if str(value).strip() else None
        else:
            card[field] = str(raw_card.get(field, "")).strip()

    if not card["knowledge_id"]:
        raise ValueError("knowledge_id cannot be empty")
    return card


def _card_exists(conn, knowledge_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM knowledge_cards WHERE knowledge_id = ?",
        (knowledge_id,),
    ).fetchone()
    return row is not None


def _write_tags(conn, knowledge_id: str, tags: list[str]) -> None:
    conn.execute("DELETE FROM card_tags WHERE knowledge_id = ?", (knowledge_id,))
    conn.executemany(
        "INSERT INTO card_tags (knowledge_id, tag) VALUES (?, ?)",
        [(knowledge_id, tag) for tag in tags],
    )


def _snapshot_payload(card: dict[str, Any]) -> str:
    return json.dumps(card, ensure_ascii=False, sort_keys=True)


def upsert_cards(cards: Iterable[dict[str, Any]], db_path=None, change_summary: str = "") -> ImportResult:
    batch_id = f"batch-{uuid.uuid4().hex[:12]}"
    created = updated = skipped = 0
    imported_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    conn = get_connection(db_path)
    try:
        for raw_card in cards:
            try:
                card = normalize_card(raw_card)
            except Exception:
                skipped += 1
                continue

            exists = _card_exists(conn, card["knowledge_id"])
            trigger_cues_json = json.dumps(card["trigger_cues"], ensure_ascii=False)

            if exists:
                existing = conn.execute(
                    "SELECT created_at, created_in_import_batch FROM knowledge_cards WHERE knowledge_id = ?",
                    (card["knowledge_id"],),
                ).fetchone()
                conn.execute(
                    """
                    UPDATE knowledge_cards
                    SET title = ?, category = ?, trigger_cues = ?, core_statement = ?,
                        optional_notes = ?, source_type = ?, source_title = ?, source_author = ?,
                        source_year = ?, source_link = ?, version = ?, created_at = ?,
                        updated_at = ?, status = ?, updated_in_import_batch = ?
                    WHERE knowledge_id = ?
                    """,
                    (
                        card["title"],
                        card["category"],
                        trigger_cues_json,
                        card["core_statement"],
                        card["optional_notes"],
                        card["source_type"],
                        card["source_title"],
                        card["source_author"],
                        card["source_year"],
                        card["source_link"],
                        card["version"],
                        existing["created_at"],
                        card["updated_at"],
                        card["status"],
                        batch_id,
                        card["knowledge_id"],
                    ),
                )
                updated += 1
            else:
                conn.execute(
                    """
                    INSERT INTO knowledge_cards (
                        knowledge_id, title, category, trigger_cues, core_statement, optional_notes,
                        source_type, source_title, source_author, source_year, source_link, version,
                        created_at, updated_at, status, created_in_import_batch, updated_in_import_batch
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        card["knowledge_id"],
                        card["title"],
                        card["category"],
                        trigger_cues_json,
                        card["core_statement"],
                        card["optional_notes"],
                        card["source_type"],
                        card["source_title"],
                        card["source_author"],
                        card["source_year"],
                        card["source_link"],
                        card["version"],
                        card["created_at"],
                        card["updated_at"],
                        card["status"],
                        batch_id,
                        batch_id,
                    ),
                )
                created += 1

            _write_tags(conn, card["knowledge_id"], card["tags"])
            conn.execute(
                """
                INSERT INTO card_versions (
                    knowledge_id, version, imported_at, import_batch_id, snapshot_json, change_summary
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    card["knowledge_id"],
                    card["version"],
                    imported_at,
                    batch_id,
                    _snapshot_payload(card),
                    change_summary,
                ),
            )

        conn.commit()
        return ImportResult(import_batch_id=batch_id, created=created, updated=updated, skipped=skipped)
    finally:
        conn.close()


def _row_to_card(conn, row) -> dict[str, Any]:
    tags = [
        tag_row["tag"]
        for tag_row in conn.execute(
            "SELECT tag FROM card_tags WHERE knowledge_id = ? ORDER BY tag",
            (row["knowledge_id"],),
        ).fetchall()
    ]
    trigger_cues = json.loads(row["trigger_cues"]) if row["trigger_cues"] else []
    versions = [
        {
            "version": version_row["version"],
            "imported_at": version_row["imported_at"],
            "import_batch_id": version_row["import_batch_id"],
            "change_summary": version_row["change_summary"],
        }
        for version_row in conn.execute(
            """
            SELECT version, imported_at, import_batch_id, change_summary
            FROM card_versions
            WHERE knowledge_id = ?
            ORDER BY id DESC
            """,
            (row["knowledge_id"],),
        ).fetchall()
    ]
    return {
        "knowledge_id": row["knowledge_id"],
        "title": row["title"],
        "category": row["category"],
        "trigger_cues": trigger_cues,
        "core_statement": row["core_statement"],
        "optional_notes": row["optional_notes"],
        "source_type": row["source_type"],
        "source_title": row["source_title"],
        "source_author": row["source_author"],
        "source_year": row["source_year"],
        "source_link": row["source_link"],
        "tags": tags,
        "microorganisms": [tag.split(":", 1)[1] for tag in tags if tag.startswith("microorganism:")],
        "operational_conditions": [tag.split(":", 1)[1] for tag in tags if tag.startswith("condition:")],
        "version": row["version"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "status": row["status"],
        "version_history": versions,
    }


def get_card(knowledge_id: str, db_path=None) -> dict[str, Any] | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM knowledge_cards WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_card(conn, row)
    finally:
        conn.close()


def search_cards(
    db_path=None,
    q: str = "",
    category: str = "",
    tags: list[str] | None = None,
    microorganism: str = "",
    condition: str = "",
    source_type: str = "",
    status: str = "active",
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    tags = tags or []
    conn = get_connection(db_path)
    try:
        sql = """
        SELECT DISTINCT kc.*
        FROM knowledge_cards kc
        LEFT JOIN card_tags ct ON kc.knowledge_id = ct.knowledge_id
        WHERE 1 = 1
        """
        params: list[Any] = []

        if q:
            sql += """
            AND (
                kc.knowledge_id LIKE ? OR
                kc.title LIKE ? OR
                kc.core_statement LIKE ? OR
                kc.optional_notes LIKE ? OR
                kc.trigger_cues LIKE ? OR
                kc.source_title LIKE ? OR
                kc.source_author LIKE ? OR
                ct.tag LIKE ?
            )
            """
            wildcard = f"%{q}%"
            params.extend([wildcard] * 8)
        if category:
            sql += " AND kc.category = ?"
            params.append(category)
        if source_type:
            sql += " AND kc.source_type = ?"
            params.append(source_type)
        if status:
            sql += " AND kc.status = ?"
            params.append(status)
        if microorganism:
            sql += " AND kc.knowledge_id IN (SELECT knowledge_id FROM card_tags WHERE tag = ?)"
            params.append(f"microorganism:{microorganism}")
        if condition:
            sql += " AND kc.knowledge_id IN (SELECT knowledge_id FROM card_tags WHERE tag = ?)"
            params.append(f"condition:{condition}")
        for tag in tags:
            sql += " AND kc.knowledge_id IN (SELECT knowledge_id FROM card_tags WHERE tag = ?)"
            params.append(tag)

        sql += " ORDER BY kc.updated_at DESC, kc.knowledge_id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(sql, params).fetchall()
        return [_row_to_card(conn, row) for row in rows]
    finally:
        conn.close()


def list_distinct_values(kind: str, db_path=None) -> list[str]:
    conn = get_connection(db_path)
    try:
        if kind == "categories":
            rows = conn.execute("SELECT DISTINCT category AS value FROM knowledge_cards ORDER BY value").fetchall()
        elif kind == "source_types":
            rows = conn.execute("SELECT DISTINCT source_type AS value FROM knowledge_cards ORDER BY value").fetchall()
        elif kind == "tags":
            rows = conn.execute("SELECT DISTINCT tag AS value FROM card_tags ORDER BY value").fetchall()
        elif kind == "microorganisms":
            rows = conn.execute(
                "SELECT DISTINCT tag AS value FROM card_tags WHERE tag LIKE 'microorganism:%' ORDER BY value"
            ).fetchall()
            return [row["value"].split(":", 1)[1] for row in rows]
        elif kind == "conditions":
            rows = conn.execute(
                "SELECT DISTINCT tag AS value FROM card_tags WHERE tag LIKE 'condition:%' ORDER BY value"
            ).fetchall()
            return [row["value"].split(":", 1)[1] for row in rows]
        else:
            raise ValueError(f"Unsupported facet kind: {kind}")
        return [row["value"] for row in rows]
    finally:
        conn.close()
