from safewatch_contracts.models import (
    ApprovalLevel,
    Detection,
    GovernanceDecision,
    PermitValidation,
    RiskAssessment,
    ViolationSeverity,
    approval_for_score,
)


class GovernanceAgent:
    def __init__(self, policy_version: str) -> None:
        self.policy_version = policy_version

    def decide(
        self,
        risk: RiskAssessment,
        detections: list[Detection],
        permit_validations: list[PermitValidation],
        contractor_id: str | None = None,
    ) -> GovernanceDecision:
        overrides: list[str] = []
        blocked_actions: list[str] = []
        triggered_rules: list[str] = []
        approval = approval_for_score(risk.risk_score)

        if any("Expired permit" in validation.issues for validation in permit_validations):
            overrides.append("expired_permit")
            blocked_actions.append("close_incident_without_hse_review")
            triggered_rules.append("hard_override.expired_permit")
            approval = max_approval(approval, ApprovalLevel.HSE_MANAGER)

        if any("Missing permit number" in validation.issues for validation in permit_validations):
            overrides.append("missing_permit_number")
            blocked_actions.append("start_or_close_work_without_hse_review")
            triggered_rules.append("hard_override.missing_permit_number")
            approval = max_approval(approval, ApprovalLevel.HSE_MANAGER)

        if contractor_id and contractor_id.lower().startswith("high-risk"):
            overrides.append("contractor_threshold")
            triggered_rules.append("hard_override.contractor_threshold")
            approval = max_approval(approval, ApprovalLevel.HSE_MANAGER)

        if any(d.violation_type == "missing_harness_at_height" or d.severity == ViolationSeverity.CRITICAL for d in detections):
            overrides.append("critical_ppe_violation")
            triggered_rules.append("hard_override.critical_ppe_violation")
            approval = max_approval(approval, ApprovalLevel.ESCALATION_COMMITTEE)

        triggered_rules.append(f"risk_band.{risk.risk_band}")

        return GovernanceDecision(
            incident_id=risk.incident_id,
            risk_score=risk.risk_score,
            risk_band=risk.risk_band,
            approval_level=approval,
            human_review_required=approval != ApprovalLevel.AUTO_LOG,
            hard_overrides=sorted(set(overrides)),
            blocked_actions=sorted(set(blocked_actions)),
            triggered_rules=triggered_rules,
            policy_version=self.policy_version,
        )


def max_approval(current: ApprovalLevel, candidate: ApprovalLevel) -> ApprovalLevel:
    order = {
        ApprovalLevel.AUTO_LOG: 0,
        ApprovalLevel.SAFETY_OFFICER: 1,
        ApprovalLevel.HSE_MANAGER: 2,
        ApprovalLevel.ESCALATION_COMMITTEE: 3,
    }
    return candidate if order[candidate] > order[current] else current
