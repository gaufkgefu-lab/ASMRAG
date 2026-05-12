from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WaterQualityRecord(BaseModel):
    date: str
    measurements: dict[str, float | None]
    units: dict[str, str] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


class ManualMicroscopyRecord(BaseModel):
    date: str
    supernatant: str | None = None
    color: str | None = None
    fi: float | None = None
    mlss: float | None = None
    taxa_counts: dict[str, float | None] = Field(default_factory=dict)
    dominant_taxon: str | None = None
    missing_fields: list[str] = Field(default_factory=list)


class ImageDerivedObservation(BaseModel):
    date: str
    source_tag: str = "future_extension"
    microorganism_detection_results: dict[str, Any] = Field(default_factory=dict)
    filament_floc_descriptors: dict[str, Any] = Field(default_factory=dict)
    settling_state_observations: dict[str, Any] = Field(default_factory=dict)
    status: str = "not_implemented"


class DayRecord(BaseModel):
    date: str
    same_day_primary_evidence: dict[str, Any]
    optional_biological_evidence: dict[str, Any] | None = None
    optional_visual_evidence: dict[str, Any] | None = None
    missing_fields: list[str] = Field(default_factory=list)
    mode_hint: str | None = None


class KnowledgeCard(BaseModel):
    card_id: str
    title: str
    trigger_cues: list[str]
    core_statement: str
    remarks: str = ""
    source: str
    source_type: str
    chunk_text: str


class RetrievedCard(BaseModel):
    card_id: str
    title: str
    score: float
    rank: int
    source: str
    source_type: str
    core_statement: str
    remarks: str = ""


class GeneratedReport(BaseModel):
    report_id: str
    date: str
    mode: str
    method: str
    llm_provider: str
    report_metadata: dict[str, Any]
    monitoring_summary: str
    diagnostic_analysis: str
    microbiology_settling_evidence: str
    follow_up_actions: list[str]
    limitations: list[str]
    auditable_statements: dict[str, float | None]
    parsed_sections: dict[str, str | list[str] | dict[str, Any] | None] = Field(default_factory=dict)
    retrieved_cards: list[RetrievedCard] = Field(default_factory=list)
    prompt_path: str | None = None


class AuditStatementResult(BaseModel):
    variable: str
    reported_value: float | None
    reference_value: float | None
    tolerance: float
    passed: bool
    note: str = ""


class AuditResult(BaseModel):
    report_id: str
    audit_consistency: float
    report_level_pass: bool
    statement_results: list[AuditStatementResult]
    audit_logs: list[str] = Field(default_factory=list)
