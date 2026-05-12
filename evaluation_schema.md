# Evaluation Schema for Direct LLM vs LLM + RAG

This document defines a minimal, revision-oriented comparison framework for two report generation settings:

1. Direct LLM without retrieval
2. LLM + RAG using retrieved engineering knowledge cards

The goal is not to claim a fully general benchmark. The goal is to support a paper revision by showing a transparent and reproducible comparison for an evidence-grounded daily reporting workflow in activated sludge operation.

## 1. Evaluation Scope

Recommended unit of comparison:

- One generated report per day
- Same input day for both conditions
- Same underlying LLM where possible
- Same decoding settings where possible
- Same output structure where possible

Recommended small experiment setup:

- Select a limited set of reporting days, for example 10 to 30 days
- Include both relatively stable days and days with mild operational concern
- Keep the experiment clearly labeled as a prototype or revision-support experiment if the dataset is small

## 2. Core Comparison Dimensions

### 2.1 Numeric Audit Consistency

Definition:
Numeric audit consistency measures whether the generated report preserves the numerical facts from the input record without adding unsupported numbers, changing values, or mixing dates.

What to check:

- Are all quoted numbers traceable to the input record for that date?
- Are input values copied correctly?
- Are trends claimed only when multiple days are actually provided to the model?
- Are derived statements cautious when no explicit threshold or validated rule is provided?

Suggested scoring:

- `2` = all reported numerical statements are traceable and correctly represented
- `1` = minor wording issue, but no materially false number
- `0` = one or more incorrect, fabricated, or date-mismatched numerical claims

Suggested summary metric:

- Mean numeric audit consistency score across test days
- Count of reports with at least one numeric inconsistency

### 2.2 Unsupported Statement Rate

Definition:
Unsupported statement rate is the proportion of substantive claims in a generated report that cannot be directly supported by:

- the provided daily operating record
- the provided microscopy notes
- retrieved knowledge cards in the RAG condition

Examples of unsupported statements:

- claiming a confirmed cause without explicit evidence
- claiming a microbiological condition that is not supported by the microscopy note
- adding operational events that were not in the input
- presenting generic textbook knowledge as if it were directly observed in the plant that day

Suggested annotation rule:

- Split the report into claim units
- Mark each claim as `supported`, `partially supported`, or `unsupported`
- Compute:
  - unsupported statement count
  - total substantive claim count
  - unsupported statement rate = unsupported / total substantive claims

Revision-oriented interpretation:

- Lower unsupported statement rate indicates better evidence discipline
- This metric is especially relevant for reviewer concerns about factual grounding and hallucination control

### 2.3 Microbiology-Related Verifiable Content

Definition:
Microbiology-related verifiable content measures whether microbiology discussion in the report is both present when relevant and verifiable from the actual microscopy input and/or retrieved cautionary knowledge.

This metric is useful because daily activated sludge reporting often includes microscopy interpretation, but such interpretation is easy for LLMs to overstate.

Suggested sub-checks:

- Does the report mention microscopy only when microscopy input exists?
- Does it correctly preserve the observed taxon and qualitative abundance?
- Does it avoid overstating ecological meaning?
- Does it convert weak evidence into follow-up checks rather than definitive diagnosis?

Suggested scoring:

- `2` = microbiology content is present when relevant and fully verifiable/cautious
- `1` = microbiology content is partly useful but slightly over-interpreted or incomplete
- `0` = microbiology content is absent when needed, unverifiable, or clearly overstated

Suggested summary metric:

- Mean microbiology verifiable content score across reports with microscopy input

## 3. Suggested Manual Expert Evaluation

For a paper revision, a small manual expert review is often more credible than a large but weakly defined automatic score.

Recommended setup:

- 2 to 3 evaluators with wastewater process or activated sludge experience
- Blind the evaluators to model condition if possible
- Randomize report order
- Evaluate paired reports for the same day

Suggested rating dimensions:

- Factual faithfulness to input data
- Practical usefulness for operator-facing daily reporting
- Appropriateness of caution level
- Quality of microbiology interpretation
- Actionability of follow-up suggestions

Suggested 5-point scale:

- `1` = poor
- `2` = weak
- `3` = acceptable
- `4` = good
- `5` = strong

Suggested expert instructions:

- Do not reward writing style alone
- Prioritize evidence grounding and operational usefulness
- Penalize confident but unsupported explanations
- Penalize fabricated microbiology interpretation

## 4. Minimal Annotation Table Template

Example fields for a manual evaluation sheet:

| field | description |
|---|---|
| date | reporting day |
| condition | direct_llm or llm_plus_rag |
| numeric_audit_score | 0, 1, or 2 |
| unsupported_claim_count | integer |
| substantive_claim_count | integer |
| unsupported_statement_rate | unsupported / substantive |
| microbiology_score | 0, 1, or 2 |
| factual_faithfulness_expert | 1 to 5 |
| operator_usefulness_expert | 1 to 5 |
| caution_appropriateness_expert | 1 to 5 |
| comments | short reviewer note |

## 5. How This Supports a Paper Revision

This schema can support revision in several ways:

- It makes the direct prompting vs RAG comparison explicit and reproducible
- It operationalizes reviewer concerns about hallucination and unsupported reasoning
- It separates numeric fidelity from higher-level interpretive quality
- It gives microbiology discussion a dedicated and verifiable assessment dimension
- It stays aligned with the original paper objective: evidence-grounded daily reporting for activated sludge operation

## 6. Important Limitations

- This is a prototype evaluation schema, not a community-standard benchmark
- If the dataset is small, results should be described as preliminary
- Knowledge cards in the demo project are placeholders and should be replaced with validated plant guidance, SOP material, or carefully curated expert knowledge
- Manual scoring criteria should be reported clearly in the revised manuscript to support transparency

Brief Chinese note:
本评价框架强调“数值一致性、无依据陈述、可核实的微生物内容”三条主线，适合用于论文大修时补强 Direct LLM 与 RAG 的可复现实验比较。
