from typing import Protocol

from safewatch_contracts.models import Detection, PermitValidation, RegulationCitation, ViolationSeverity


class RegulationSearchClient(Protocol):
    def search(self, query: str, top: int = 5) -> list[RegulationCitation]:
        ...


class ComplianceRagAgent:
    def __init__(self, index_version: str, search_client: RegulationSearchClient | None = None) -> None:
        self.index_version = index_version
        self.search_client = search_client

    def retrieve(
        self,
        detections: list[Detection],
        permit_validations: list[PermitValidation],
    ) -> list[RegulationCitation]:
        if self.search_client:
            query = build_regulation_query(detections, permit_validations)
            citations = self.search_client.search(query, top=5)
            if citations:
                return citations

        return self._fallback_retrieve(detections, permit_validations)

    def _fallback_retrieve(
        self,
        detections: list[Detection],
        permit_validations: list[PermitValidation],
    ) -> list[RegulationCitation]:
        citations: list[RegulationCitation] = []

        if any(d.severity in {ViolationSeverity.HIGH, ViolationSeverity.CRITICAL} for d in detections):
            citations.append(
                RegulationCitation(
                    source="ISO 45001",
                    clause_id="8.1",
                    title="Operational planning and control",
                    excerpt="Organizations must plan, implement, control and maintain processes needed to meet OH&S requirements.",
                    relevance_score=0.88,
                    index_version=self.index_version,
                )
            )

        if any(not validation.is_valid for validation in permit_validations):
            citations.append(
                RegulationCitation(
                    source="OSHAD",
                    clause_id="Permit-to-work",
                    title="Permit control before hazardous work",
                    excerpt="High-risk work must be controlled through valid authorization before work starts.",
                    relevance_score=0.86,
                    index_version=self.index_version,
                )
            )

        if not citations:
            citations.append(
                RegulationCitation(
                    source="ISO 45001",
                    clause_id="9.1",
                    title="Monitoring, measurement, analysis and performance evaluation",
                    excerpt="Organizations must evaluate OH&S performance and retain documented evidence of monitoring results.",
                    relevance_score=0.72,
                    index_version=self.index_version,
                )
            )

        return citations


def build_regulation_query(
    detections: list[Detection],
    permit_validations: list[PermitValidation],
) -> str:
    terms: list[str] = ["occupational health safety compliance"]
    for detection in detections:
        if detection.violation_type:
            terms.append(detection.violation_type.replace("_", " "))
        terms.append(f"{detection.severity} ppe violation")

    for validation in permit_validations:
        terms.append(validation.document_type.replace("_", " "))
        if validation.work_type:
            terms.append(validation.work_type.replace("_", " "))
        if validation.issues:
            terms.extend(validation.issues)
        terms.append("valid permit before hazardous work" if validation.is_valid else "invalid permit hazardous work")

    return " ".join(terms)
