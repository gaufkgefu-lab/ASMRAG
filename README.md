# ASMRAG

ASMRAG is a Python prototype for evidence-grounded daily reporting in activated sludge operation. It compares direct report generation with retrieval-augmented generation (RAG), with special attention to auditable numerical claims and same-day process evidence.

## What Is Included

- A lightweight baseline pipeline for direct LLM reporting.
- A lightweight RAG pipeline using curated knowledge cards.
- A fuller evidence reporting workflow under `evidence_reporting_project/`.
- Prompt templates, report schemas, numeric auditing utilities, and unit tests.
- Small example CSV files for demonstrating the minimal root-level pipeline.

## What Is Not Included

The repository intentionally excludes local data and generated vector knowledge bases:

- `shujv/`
- `evidence_reporting_project/data/`
- `zhishiku_kb/`
- `.env`
- generated outputs and Python caches

These paths are listed in `.gitignore` so that private data, generated artifacts, API keys, and local indexes are not uploaded to GitHub.

## Repository Layout

```text
.
|-- baseline_pipeline.py              # Direct LLM baseline prototype
|-- rag_pipeline.py                   # Retrieval-augmented prototype
|-- prompts.py                        # Prompt templates
|-- vector_kb.py                      # Local vector/lexical knowledge-base helper
|-- build_zhishiku_kb.py              # Script for building the local knowledge base
|-- evaluation_schema.md              # Evaluation guidance
|-- *_example.csv                     # Small demonstration inputs
|-- zhishiku/                         # Small text knowledge-source examples
|-- evidence_reporting_project/       # Main reproducible workflow
`-- README_zhishiku_kb.md             # Notes for local knowledge-base building
```

## Main Workflow

The more complete workflow lives in `evidence_reporting_project/`.

Implemented components include:

- day-level evidence organization
- retrieval cue extraction
- knowledge-card construction
- TF-IDF based retrieval
- constrained prompt assembly
- report generation with mock or DeepSeek clients
- numerical audit checks
- summary metrics and smoke tests

Mode C vision support is reserved as an interface only and is not implemented in the current stage.

## Environment

Python 3.11 or newer is recommended.

Install dependencies for the main workflow:

```powershell
cd evidence_reporting_project
python -m pip install -r requirements.txt
```

For real LLM calls, copy the example environment file and fill in your key:

```powershell
copy .env.example .env
```

The `.env` file is ignored by Git.

## Quick Start

Run the root-level direct baseline:

```powershell
python baseline_pipeline.py --date 2022-07-14
```

Run the root-level RAG prototype:

```powershell
python rag_pipeline.py --date 2022-07-14
```

Run the main project with mock LLM:

```powershell
cd evidence_reporting_project
python scripts/run_mode_a.py --date 20220603 --llm-provider mock
python scripts/run_mode_b.py --date 20220603 --llm-provider mock
```

Run tests:

```powershell
cd evidence_reporting_project
python -m unittest discover -s tests -v
```

## Local Data Notes

For local experiments, place private process records, microscopy records, and generated knowledge-base artifacts in ignored directories. For example:

```text
D:\python\shujv
D:\python\zhishiku_kb
D:\python\evidence_reporting_project\data
```

These files stay on the local machine and are not part of the GitHub repository.
