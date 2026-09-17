from safewatch_api.schemas import ReviewerPacket
from safewatch_contracts.models import Detection, GovernanceDecision, PermitValidation, RegulationCitation


class ReportAgent:
    def build_packet(
        self,
        incident_id: str,
        detections: list[Detection],
        permit_validations: list[PermitValidation],
        citations: list[RegulationCitation],
        governance: GovernanceDecision,
    ) -> ReviewerPacket:
        findings: list[str] = []
        findings.extend(
            f"{d.violation_type or 'no_violation'} severity={d.severity} confidence={d.confidence:.2f}"
            for d in detections
        )
        findings.extend(
            f"{v.document_type} valid={v.is_valid} issues={', '.join(v.issues) if v.issues else 'none'}"
            for v in permit_validations
        )

        summary = (
            f"Incident {incident_id} scored {governance.risk_score} "
            f"({governance.risk_band}) and routes to {governance.approval_level}."
        )

        return ReviewerPacket(
            incident_id=incident_id,
            summary=summary,
            required_approval=governance.approval_level,
            citations=citations,
            key_findings=findings,
        )

