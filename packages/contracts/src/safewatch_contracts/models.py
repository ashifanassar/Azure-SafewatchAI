from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class ViolationSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskBand(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalLevel(StrEnum):
    AUTO_LOG = "auto_log"
    SAFETY_OFFICER = "safety_officer"
    HSE_MANAGER = "hse_manager"
    ESCALATION_COMMITTEE = "escalation_committee"


class IncidentStatus(StrEnum):
    DRAFT = "draft"
    ANALYZING = "analyzing"
    PENDING_REVIEW = "pending_review"
    AUTO_LOGGED = "auto_logged"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    CLOSED = "closed"
    FAILED = "failed"


class EvidenceType(StrEnum):
    IMAGE = "image"
    PERMIT = "permit"
    DOCUMENT = "document"
    REPORT = "report"


class Detection(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    detection_id: UUID = Field(default_factory=uuid4)
    incident_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    worker_count: int = Field(ge=0)
    violation_type: str | None = None
    severity: ViolationSeverity = ViolationSeverity.LOW
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_boxes: list[dict[str, float]] = Field(default_factory=list)
    model_version: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def require_violation_when_severity_is_not_low(self) -> "Detection":
        if self.severity != ViolationSeverity.LOW and not self.violation_type:
            raise ValueError("violation_type is required for medium, high, or critical detections")
        return self


class PermitValidation(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    validation_id: UUID = Field(default_factory=uuid4)
    incident_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    is_valid: bool
    permit_number: str | None = None
    work_type: str | None = None
    expiry_at: datetime | None = None
    issues: list[str] = Field(default_factory=list)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    model_version: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def invalid_permits_need_issues(self) -> "PermitValidation":
        if not self.is_valid and not self.issues:
            raise ValueError("invalid permit validations must include at least one issue")
        return self


class RegulationCitation(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    citation_id: UUID = Field(default_factory=uuid4)
    source: str = Field(min_length=1)
    clause_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    excerpt: str = Field(min_length=1, max_length=1200)
    relevance_score: float = Field(ge=0.0, le=1.0)
    index_version: str = Field(min_length=1)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RiskAssessment(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    assessment_id: UUID = Field(default_factory=uuid4)
    incident_id: str = Field(min_length=1)
    risk_score: int = Field(ge=0, le=100)
    risk_band: RiskBand
    factor_breakdown: dict[str, int] = Field(default_factory=dict)
    explanation: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("factor_breakdown")
    @classmethod
    def factor_values_must_be_scores(cls, value: dict[str, int]) -> dict[str, int]:
        for factor, score in value.items():
            if score < 0:
                raise ValueError(f"{factor} score cannot be negative")
        return value

    @model_validator(mode="after")
    def band_must_match_score(self) -> "RiskAssessment":
        expected = band_for_score(self.risk_score)
        if self.risk_band != expected:
            raise ValueError(f"risk_band must be {expected} for score {self.risk_score}")
        return self


class GovernanceDecision(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    decision_id: UUID = Field(default_factory=uuid4)
    incident_id: str = Field(min_length=1)
    risk_score: int = Field(ge=0, le=100)
    risk_band: RiskBand
    approval_level: ApprovalLevel
    human_review_required: bool
    hard_overrides: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    triggered_rules: list[str] = Field(default_factory=list)
    policy_version: str = Field(min_length=1)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def approval_level_must_match_governance_rules(self) -> "GovernanceDecision":
        expected = approval_for_score(self.risk_score)
        if self.approval_level != expected and not self.hard_overrides:
            raise ValueError("approval_level must match risk score unless hard_overrides explain escalation")
        if self.risk_score >= 30 and not self.human_review_required:
            raise ValueError("risk_score >= 30 must require human review")
        if self.risk_score < 30 and self.approval_level == ApprovalLevel.AUTO_LOG and self.human_review_required:
            raise ValueError("auto-log decisions should not require human review")
        return self


class IncidentRecord(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    incident_id: str = Field(min_length=1)
    site_id: str = Field(min_length=1)
    zone_id: str | None = None
    work_type: str | None = None
    contractor_id: str | None = None
    status: IncidentStatus = IncidentStatus.DRAFT
    evidence_ids: list[str] = Field(default_factory=list)
    agent_run_ids: list[str] = Field(default_factory=list)
    created_by: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentRun(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    agent_run_id: str = Field(min_length=1)
    incident_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    status: Literal["started", "succeeded", "failed", "timed_out"]
    input_refs: list[str] = Field(default_factory=list)
    output_ref: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    policy_version: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def failed_runs_need_error_message(self) -> "AgentRun":
        if self.status in {"failed", "timed_out"} and not self.error_message:
            raise ValueError("failed or timed_out agent runs must include error_message")
        return self


class AuditEvent(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    audit_event_id: UUID = Field(default_factory=uuid4)
    incident_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    actor_type: Literal["user", "system", "agent"]
    actor_id: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def band_for_score(score: int) -> RiskBand:
    if score < 30:
        return RiskBand.LOW
    if score < 60:
        return RiskBand.MEDIUM
    if score < 80:
        return RiskBand.HIGH
    return RiskBand.CRITICAL


def approval_for_score(score: int) -> ApprovalLevel:
    if score < 30:
        return ApprovalLevel.AUTO_LOG
    if score < 60:
        return ApprovalLevel.SAFETY_OFFICER
    if score < 80:
        return ApprovalLevel.HSE_MANAGER
    return ApprovalLevel.ESCALATION_COMMITTEE

