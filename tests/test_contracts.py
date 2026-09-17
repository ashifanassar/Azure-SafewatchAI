import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "contracts" / "src"))

from safewatch_contracts.models import (  # noqa: E402
    AgentRun,
    ApprovalLevel,
    AuditEvent,
    Detection,
    GovernanceDecision,
    IncidentRecord,
    PermitValidation,
    RegulationCitation,
    RiskAssessment,
    RiskBand,
    ViolationSeverity,
    approval_for_score,
    band_for_score,
)


class ContractTests(unittest.TestCase):
    def test_detection_requires_violation_for_high_severity(self) -> None:
        with self.assertRaises(ValidationError):
            Detection(
                incident_id="inc-1",
                evidence_id="ev-1",
                worker_count=1,
                severity=ViolationSeverity.HIGH,
                confidence=0.9,
                model_version="ppe-v1",
            )

    def test_invalid_permit_requires_issue(self) -> None:
        with self.assertRaises(ValidationError):
            PermitValidation(
                incident_id="inc-1",
                evidence_id="ev-2",
                document_type="permit_to_work",
                is_valid=False,
                model_version="doc-intel-v1",
            )

    def test_regulation_citation_score_is_bounded(self) -> None:
        with self.assertRaises(ValidationError):
            RegulationCitation(
                source="ISO 45001",
                clause_id="8.1",
                title="Operational planning and control",
                excerpt="Controls must be established for safety risks.",
                relevance_score=1.2,
                index_version="rag-index-v1",
            )

    def test_risk_band_must_match_score(self) -> None:
        with self.assertRaises(ValidationError):
            RiskAssessment(
                incident_id="inc-1",
                risk_score=72,
                risk_band=RiskBand.MEDIUM,
                factor_breakdown={"ppe_severity": 30},
                explanation="Missing harness at height.",
                policy_version="risk-policy-v1",
            )

    def test_risk_band_boundaries(self) -> None:
        self.assertEqual(band_for_score(29), RiskBand.LOW)
        self.assertEqual(band_for_score(30), RiskBand.MEDIUM)
        self.assertEqual(band_for_score(59), RiskBand.MEDIUM)
        self.assertEqual(band_for_score(60), RiskBand.HIGH)
        self.assertEqual(band_for_score(79), RiskBand.HIGH)
        self.assertEqual(band_for_score(80), RiskBand.CRITICAL)

    def test_approval_boundaries(self) -> None:
        self.assertEqual(approval_for_score(29), ApprovalLevel.AUTO_LOG)
        self.assertEqual(approval_for_score(30), ApprovalLevel.SAFETY_OFFICER)
        self.assertEqual(approval_for_score(60), ApprovalLevel.HSE_MANAGER)
        self.assertEqual(approval_for_score(80), ApprovalLevel.ESCALATION_COMMITTEE)

    def test_governance_requires_human_gate_for_risk_30_or_above(self) -> None:
        with self.assertRaises(ValidationError):
            GovernanceDecision(
                incident_id="inc-1",
                risk_score=30,
                risk_band=RiskBand.MEDIUM,
                approval_level=ApprovalLevel.SAFETY_OFFICER,
                human_review_required=False,
                policy_version="governance-policy-v1",
            )

    def test_governance_allows_auto_log_below_30(self) -> None:
        decision = GovernanceDecision(
            incident_id="inc-1",
            risk_score=20,
            risk_band=RiskBand.LOW,
            approval_level=ApprovalLevel.AUTO_LOG,
            human_review_required=False,
            policy_version="governance-policy-v1",
        )
        self.assertEqual(decision.approval_level, ApprovalLevel.AUTO_LOG)

    def test_agent_run_failure_requires_error_message(self) -> None:
        with self.assertRaises(ValidationError):
            AgentRun(
                agent_run_id="run-1",
                incident_id="inc-1",
                agent_name="rag-agent",
                correlation_id="corr-1",
                status="failed",
            )

    def test_incident_and_audit_models_capture_traceability(self) -> None:
        incident = IncidentRecord(
            incident_id="inc-1",
            site_id="site-1",
            created_by="ashifa",
        )
        event = AuditEvent(
            incident_id=incident.incident_id,
            correlation_id="corr-1",
            event_type="governance_decision_recorded",
            actor_type="agent",
            actor_id="governance-agent",
            payload={"policy_version": "governance-policy-v1"},
        )
        self.assertEqual(event.payload["policy_version"], "governance-policy-v1")


if __name__ == "__main__":
    unittest.main()

