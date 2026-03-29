# Activated Sludge Daily Reporting RAG Prototype

This repository is a minimal, editable Python prototype for comparing:

1. Direct LLM without RAG
2. LLM + RAG

The intended application is operator-facing daily report generation for activated sludge operation.

The core objective is intentionally narrow and revision-oriented:

> an evidence-grounded daily reporting workflow for activated sludge operation

This prototype is designed to help support a paper revision. It is not intended to redefine the paper into a different topic. In particular, Mode C or vision-based detection is not implemented here as a main research direction. If needed, it should remain a placeholder interface outside this minimal prototype.

## Folder Structure

```text
activated_sludge_rag_prototype/
├── README.md
├── evaluation_schema.md
├── prompts.py
├── baseline_pipeline.py
├── rag_pipeline.py
├── knowledge_cards_example.csv
├── daily_records_example.csv
├── microscopy_example.csv
└── outputs/                      # created automatically after running scripts
```

## What Each File Does

### `knowledge_cards_example.csv`

Small example knowledge base in card format.

Columns:

- `id`
- `title`
- `trigger_cues`
- `core_statement`
- `caution`
- `source`

These cards are intentionally conservative and engineering-oriented. They are placeholders for reproducible RAG experiments and should be replaced with validated plant guidance, SOP content, or a curated expert knowledge base.

### `daily_records_example.csv`

Example daily operating records for a few days.

Included fields:

- `date`
- `DO`
- `MLSS`
- `SV30`
- `SVI`
- `COD_in`
- `COD_out`
- `pH`
- `temperature`
- `NH4_N_out`
- `return_sludge_ratio`
- `notes`

All values are demo values only. They are realistic-looking examples, not real experimental results.

### `microscopy_example.csv`

Example same-day microscopy observations in a simple table.

Columns:

- `date`
- `taxon`
- `abundance`
- `note`

This file supports microbiology-aware reporting while keeping claims conservative and verifiable.

### `prompts.py`

Contains two English prompt templates:

- direct LLM baseline prompt
- RAG prompt with retrieved evidence

Chinese comments are included after each prompt template to explain the intended behavior.

### `baseline_pipeline.py`

Minimal baseline pipeline for direct prompting.

It:

- reads daily records
- optionally reads same-day microscopy data
- builds the direct prompt
- calls a placeholder LLM function
- saves the output as structured JSON

### `rag_pipeline.py`

Minimal RAG pipeline.

It:

- reads daily records
- reads microscopy observations
- reads knowledge cards
- performs lightweight retrieval
- builds a RAG prompt with retrieved evidence
- calls a placeholder LLM function
- saves the output as structured JSON

The retrieval method is intentionally simple:

- TF-IDF style lexical scoring
- keyword-overlap fallback when no embedding model is available

This keeps the prototype easy to run and easy to explain in a revision.

### `evaluation_schema.md`

Provides a practical comparison schema for Direct LLM vs LLM + RAG, including:

- numeric audit consistency
- unsupported statement rate
- microbiology-related verifiable content
- a small expert evaluation setup

## How to Run

Use Python 3.9+ if possible.

### 1. Run the direct LLM baseline

```bash
python baseline_pipeline.py --date 2022-07-14
```

### 2. Run the RAG pipeline

```bash
python rag_pipeline.py --date 2022-07-14
```

### 3. Check saved outputs

Both scripts save JSON files into `outputs/` by default.

Example output files:

- `outputs/baseline_report_2022-07-14.json`
- `outputs/rag_report_2022-07-14.json`

## What Is Placeholder or Demo Content

The following items are placeholders and must be replaced before any serious experiment:

- example CSV values
- knowledge card content
- LLM API function in `call_llm()`
- `YOUR_MODEL_NAME`
- `YOUR_API_KEY`

Search for these markers:

- `TODO: replace with real plant data`
- `YOUR_MODEL_NAME`
- `YOUR_API_KEY`
- `PLACEHOLDER OUTPUT`

## Recommended Replacement Path for a Real Revision Experiment

1. Replace `daily_records_example.csv` with real plant daily record data.
2. Replace `microscopy_example.csv` with same-day microscopy observations using a consistent observation format.
3. Replace `knowledge_cards_example.csv` with a curated card-based engineering knowledge base.
4. Implement the actual model call in both pipelines.
5. Keep the same model, temperature, and output structure across baseline and RAG conditions.
6. Evaluate generated reports using the schema in `evaluation_schema.md`.

## How This Prototype Supports a Paper Revision

This prototype can help address common revision requests such as:

- clearer input representation
- clearer knowledge-base construction
- clearer reproducibility
- stronger comparison between direct prompting and retrieval-augmented generation

The code is intentionally minimal so that reviewers and co-authors can inspect:

- what data are provided to the model
- what additional evidence is retrieved in the RAG condition
- where unsupported inference could enter the pipeline
- how outputs are saved for later audit

## Important Limitations

- This repository does not contain a real production deployment pipeline.
- It does not include actual model credentials or a real API integration.
- It does not claim experimental performance.
- It does not include a full embedding retrieval stack.
- It does not include vision-based detection as a main module.
- Knowledge cards in this demo are placeholders, not formal published citations.

Brief Chinese note:
这个原型的重点是把“大修时需要补清楚的实验逻辑”落成一个最小可复现骨架，而不是直接声称新的正式实验结果。
