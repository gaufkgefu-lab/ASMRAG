"""Database helpers for the public engineering knowledge base."""

from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTANCE_DIR = PROJECT_ROOT / "instance"
DEFAULT_DB_PATH = INSTANCE_DIR / "knowledge_base.db"


def ensure_instance_dir() -> None:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    ensure_instance_dir()
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_cards (
    knowledge_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    trigger_cues TEXT NOT NULL,
    core_statement TEXT NOT NULL,
    optional_notes TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL,
    source_title TEXT NOT NULL,
    source_author TEXT NOT NULL,
    source_year INTEGER,
    source_link TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL,
    created_in_import_batch TEXT,
    updated_in_import_batch TEXT
);

CREATE TABLE IF NOT EXISTS card_tags (
    knowledge_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (knowledge_id, tag),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_cards(knowledge_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS card_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id TEXT NOT NULL,
    version TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    import_batch_id TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    change_summary TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_cards(knowledge_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cards_category ON knowledge_cards(category);
CREATE INDEX IF NOT EXISTS idx_cards_source_type ON knowledge_cards(source_type);
CREATE INDEX IF NOT EXISTS idx_cards_status ON knowledge_cards(status);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON card_tags(tag);
CREATE INDEX IF NOT EXISTS idx_versions_knowledge_id ON card_versions(knowledge_id);
"""


def init_db(db_path: Path | str | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
