# AGENTS.md

This repository hosts the public engineering knowledge base for the ASMRAG activated sludge RAG workflow.

## Project Intent

The system exists to store, version, search, and publish engineering knowledge cards used in an evidence-grounded reporting workflow for activated sludge operation.

Keep the scope anchored to:

- activated sludge operation
- operator-facing reporting support
- source traceability
- conservative, verification-oriented statements

Do not redesign the repository into a generic chatbot project.
Do not turn visual detection or Mode C features into the main architecture.

## Architecture Rules

- Backend stack: FastAPI + SQLite by default.
- Frontend stack: server-rendered Jinja templates unless there is a strong reason to add a richer client.
- Import/update workflow: CSV or JSON files are the canonical editable inputs.
- Version history must be preserved for every imported card.
- Public card pages must always display source metadata and version information.

## Card Design Rules

Each card must express exactly one of the following:

- one interpretable engineering relation
- one microorganism-condition association
- one verification-oriented caution

Do not merge unrelated ideas into one card.
If source details are incomplete, use clearly labeled placeholders instead of inventing citations.
Keep claims conservative and suitable for engineering review.

## Tagging Conventions

Use plain tags for general topics, for example:

- `DO`
- `settling`
- `microscopy`

Use prefixed tags for filter facets:

- `microorganism:<name>`
- `condition:<name>`

## Update Workflow

1. Edit or add cards in `data/*.csv` or `data/*.json`.
2. Run `python scripts/init_db.py` if needed.
3. Run `python scripts/import_cards.py data/seed_cards.json --change-summary "short note"`.
4. Start the site with `uvicorn app.main:app --reload`.
5. Confirm the updated card appears on the website and in `/api/cards`.

## Coding Style

- Keep modules small and explicit.
- Prefer standard-library utilities where practical.
- Avoid hidden framework magic for import and query logic.
- Preserve readability over abstraction.
- Add new dependencies only when they clearly reduce maintenance burden.

## Verification Expectations

When changing this repository, verify at minimum:

- database initialization works
- import script works
- `/api/cards` and card detail retrieval work once dependencies are installed
- source metadata remains visible on the public detail page
- version history is still recorded after re-import
