# Evidence-Grounded Daily Reporting

This project implements a reproducible Python workflow for evidence-grounded daily reporting in activated sludge operation.

Implemented in the current stage:

- Day-level evidence organization
- Retrieval-grounded report generation
- Numerical cross-checking
- Mode A: process and water-quality records only
- Mode B: Mode A plus same-day manual microscopy records

Reserved but not implemented:

- Mode C vision pathway

## Project layout

```text
evidence_reporting_project/
  configs/
  data/
  prompts/
  scripts/
  src/
  tests/
  outputs/
```

## Environment

Python `3.11+` is recommended.

Install dependencies:

```powershell
pip install -r requirements.txt
```

The code also includes small fallbacks for local smoke testing when `pandas`, `jinja2`, `pyyaml`, or `scikit-learn` are unavailable, but the main path is designed around those libraries.

## Configure LLM

Copy `.env.example` to `.env` and fill in your key if you want to call DeepSeek.

```powershell
copy .env.example .env
```

For local smoke testing the default scripts use `mock` mode and do not call an external API.

## Input data

Expected main inputs:

- `water_quality.csv`
- `manual_microscopy.csv`
- `knowledge_sources/*.txt`
- optional `image_observations.csv` for future Mode C compatibility only

The project includes example data under `data/examples/`.

For your current dataset:

- process and water-quality records: `D:\python\shujv\Process_variables.csv`
- manual microscopy records: `D:\python\shujv\Manual_microscopy.csv`
- knowledge texts: `D:\python\zhishiku`

## Quick start

Build knowledge cards:

```powershell
python scripts/build_kb.py --input-dir D:\python\zhishiku --output data\knowledge_base\knowledge_cards.jsonl
```

Run Mode A with mock LLM:

```powershell
python scripts/run_mode_a.py --date 20220603 --llm-provider mock
```

Run Mode B with mock LLM:

```powershell
python scripts/run_mode_b.py --date 20220603 --llm-provider mock
```

Run auditing only:

```powershell
python scripts/run_audit.py --report outputs\reports\mode_a_20220603_rag_mock_report.json
```

Run ablation:

```powershell
python scripts/run_ablation.py --dates 20220601,20220603,20220604 --llm-provider mock
```

Run tests:

```powershell
python -m unittest discover -s tests -v
```

## Workflow mapping to the paper

1. `evidence_builder.py`
   Builds unified day-level evidence from same-day records.
2. `query_cue_extractor.py`
   Produces structured retrieval cues from anomalies, microscopy observations, missing fields, and placeholder settling slots.
3. `knowledge_card_builder.py`
   Segments long knowledge sources into normalized knowledge cards.
4. `retriever.py`
   Builds TF-IDF plus cosine retrieval over knowledge cards.
5. `prompt_builder.py`
   Assembles constrained prompts for Mode A and Mode B.
6. `report_generator.py`
   Produces fixed-schema reports using either the mock generator or DeepSeek client.
7. `numeric_auditor.py`
   Cross-checks auditable numerical statements against same-day reference values.
8. `metrics.py`
   Computes audit consistency, report-level pass rate, average report length, and section completeness.

## Mode C status

Mode C is intentionally not implemented in the current stage.

Reserved files and interfaces:

- `src/mode_c_interface.py`
- `ImageDerivedObservation` in `src/data_models.py`
- `optional_visual_evidence` in day-level evidence
- `image_observations.csv` handling hooks in the pipeline

Any direct Mode C execution raises:

```python
NotImplementedError(
    "Mode C is reserved as a future extension and is not implemented in the current stage."
)
```
