from safewatch_contracts.models import (
    Detection,
    PermitValidation,
    RiskAssessment,
    ViolationSeverity,
    band_for_score,
)


class RiskScoringAgent:
    def __init__(self, policy_version: str) -> None:
        self.policy_version = policy_version

    def assess(
        self,
        incident_id: str,
        detections: list[Detection],
        permit_validations: list[PermitValidation],
        contractor_id: str | None = None,
    ) -> RiskAssessment:
        factors = {
            "ppe_severity": self._ppe_score(detections),
            "permit_status": self._permit_score(permit_validations),
            "contractor_history": 15 if contractor_id and contractor_id.lower().startswith("high-risk") else 0,
        }
        score = min(100, sum(factors.values()))
        explanations = [f"{name}={value}" for name, value in factors.items() if value]
        explanation = "Composite weighted score from " + (", ".join(explanations) if explanations else "no material violations")

        return RiskAssessment(
            incident_id=incident_id,
            risk_score=score,
            risk_band=band_for_score(score),
            factor_breakdown=factors,
            explanation=explanation,
            policy_version=self.policy_version,
        )

    @staticmethod
    def _ppe_score(detections: list[Detection]) -> int:
        severity_scores = {
            ViolationSeverity.LOW: 0,
            ViolationSeverity.MEDIUM: 25,
            ViolationSeverity.HIGH: 45,
            ViolationSeverity.CRITICAL: 65,
        }
        return max((severity_scores[ViolationSeverity(d.severity)] for d in detections), default=0)

    @staticmethod
    def _permit_score(validations: list[PermitValidation]) -> int:
        if any("Expired permit" in validation.issues for validation in validations):
            return 35
        if any(not validation.is_valid for validation in validations):
            return 20
        return 0

