# ASMRAG Public Engineering Knowledge Base

This repository implements a lightweight public knowledge base system for the engineering knowledge used by an activated sludge RAG workflow.

It stores structured knowledge cards, source metadata, category labels, tags, and version history, and exposes them through:

- a public-facing website for browsing cards
- a machine-readable API for search and retrieval

The implementation uses:

- FastAPI for the backend API and website routing
- Jinja templates for the public website
- SQLite for storage
- CSV or JSON for editable card imports

## Repository Structure

```text
ASMRAG/
├── AGENTS.md
├── README.md
├── requirements.txt
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── db.py
│   ├── main.py
│   ├── repository.py
│   ├── static/style.css
│   └── templates/
├── data/
│   ├── seed_cards.csv
│   └── seed_cards.json
├── scripts/
│   ├── import_cards.py
│   └── init_db.py
└── instance/
    └── knowledge_base.db
```

## Database Schema

The SQLite schema contains three tables:

1. `knowledge_cards`
   Stores the current state of each card.
2. `card_tags`
   Stores normalized tags for filters and faceted browsing.
3. `card_versions`
   Stores a snapshot for every imported card version.

Each card includes:

- `knowledge_id`
- `title`
- `category`
- `trigger_cues`
- `core_statement`
- `optional_notes`
- `source_type`
- `source_title`
- `source_author`
- `source_year`
- `source_link`
- `tags`
- `version`
- `created_at`
- `updated_at`
- `status`

## Seed Data

Sample cards are included in:

- `data/seed_cards.json`
- `data/seed_cards.csv`

The sample set contains:

- one process-context example from your prompt
- several microorganism-condition associations conservatively derived from `微生物种类与工况关系表.xlsx`
- traceability and verification-oriented caution cards

When source details are incomplete, placeholders are used intentionally rather than invented citations.

## Local Setup

### 1. Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Initialize the database

```powershell
python scripts/init_db.py
```

### 4. Import sample cards

```powershell
python scripts/import_cards.py data/seed_cards.json --change-summary "Initial seed import"
```

You can also import the CSV version:

```powershell
python scripts/import_cards.py data/seed_cards.csv --change-summary "Initial CSV import"
```

### 5. Run the website and API

```powershell
uvicorn app.main:app --reload
```

Open:

- Website: `http://127.0.0.1:8000/`
- API: `http://127.0.0.1:8000/api/cards`

## API Overview

### `GET /api/health`

Simple health check.

### `GET /api/cards`

Supports:

- keyword search with `q`
- `category`
- `tag`
- `microorganism`
- `condition`
- `source_type`
- `status`
- `limit`
- `offset`

Example:

```text
/api/cards?q=DO&condition=low_DO
```

### `GET /api/cards/{knowledge_id}`

Returns one card with:

- source metadata
- normalized tags
- derived microorganism and condition facets
- version history

### `GET /api/facets`

Returns:

- categories
- tags
- microorganisms
- conditions
- source types

## Public Website Features

The public website supports:

- keyword search
- category filtering
- tag filtering
- microorganism filtering
- operational-condition filtering
- source-type filtering
- per-card source traceability
- per-card version history

## Import and Update Workflow

The import script performs an upsert by `knowledge_id`:

- new cards are inserted
- existing cards are updated
- every import writes a snapshot to `card_versions`

Recommended workflow:

1. Edit `data/*.csv` or `data/*.json`.
2. Increase `version` if the card meaning changes.
3. Update `updated_at`.
4. Run the import command with `--change-summary`.
5. Review the updated detail page and API output.

## Tagging Conventions

Use general tags such as:

- `DO`
- `settling`
- `microscopy`

Use prefixed tags for filter facets:

- `microorganism:<name>`
- `condition:<name>`

Examples:

- `microorganism:侧滴虫`
- `condition:low_DO`

## Limitations

- This is a lightweight academic prototype, not a multi-user production CMS.
- Full-text search uses SQL `LIKE`, not a dedicated search engine.
- Authentication and editorial approval flows are not included.
- Spreadsheet-derived cards should be replaced or expanded with validated sources over time.

Brief Chinese note:
这个仓库把 activated sludge RAG 所需的工程知识卡做成了一个可导入、可检索、可公开浏览、可追溯版本的小型系统。
