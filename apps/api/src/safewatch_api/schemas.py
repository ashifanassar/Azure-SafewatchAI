from typing import Any, Literal

from pydantic import BaseModel, Field

from safewatch_contracts.models import (
    Detection,
    GovernanceDecision,
    IncidentRecord,
    PermitValidation,
    RegulationCitation,
    RiskAssessment,
)


class EvidenceRef(BaseModel):
    evidence_id: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    kind: Literal["image", "permit", "document"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceUploadResponse(BaseModel):
    evidence_id: str
    uri: str
    kind: Literal["image", "permit", "document"]
    filename: str
    content_type: str | None = None


class AnalyzeIncidentRequest(BaseModel):
    incident_id: str = Field(min_length=1)
    site_id: str = Field(min_length=1)
    zone_id: str | None = None
    work_type: str | None = None
    contractor_id: str | None = None
    created_by: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ReviewerPacket(BaseModel):
    incident_id: str
    summary: str
    required_approval: str
    citations: list[RegulationCitation]
    key_findings: list[str] = Field(default_factory=list)


class WorkflowResult(BaseModel):
    incident: IncidentRecord
    detections: list[Detection]
    permit_validations: list[PermitValidation]
    citations: list[RegulationCitation]
    risk: RiskAssessment
    governance: GovernanceDecision
    reviewer_packet: ReviewerPacket


class ReviewDecisionRequest(BaseModel):
    action: Literal["approve", "reject"]
    reviewer_id: str = Field(min_length=1)
    comment: str | None = None


class ReviewDecisionResponse(BaseModel):
    incident_id: str
    status: Literal["approved", "rejected"]
    reviewer_id: str
    comment: str | None = None
