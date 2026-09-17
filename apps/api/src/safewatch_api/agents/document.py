from datetime import datetime, timezone
from typing import Protocol

from safewatch_api.schemas import EvidenceRef
from safewatch_contracts.models import PermitValidation


class BlobReader(Protocol):
    def read(self, uri: str) -> bytes: ...


class DocumentExtractor(Protocol):
    def extract(self, document_bytes: bytes) -> dict: ...


class DocumentAgent:
    def __init__(
        self,
        model_version: str,
        blob_reader: BlobReader | None = None,
        extractor: DocumentExtractor | None = None,
    ) -> None:
        self.model_version = model_version
        self.blob_reader = blob_reader
        self.extractor = extractor

    def validate(self, incident_id: str, evidence: list[EvidenceRef]) -> list[PermitValidation]:
        validations: list[PermitValidation] = []
        for item in evidence:
            if item.kind not in {"permit", "document"}:
                continue

            metadata = self._metadata_for(item)
            expiry_raw = metadata.get("expiry_at")
            expiry_at = self._parse_datetime(expiry_raw)
            issues: list[str] = []

            if item.kind == "permit" and not metadata.get("permit_number"):
                issues.append("Missing permit number")
            if expiry_at and expiry_at < datetime.now(timezone.utc):
                issues.append("Expired permit")
            if metadata.get("status") == "expired":
                issues.append("Expired permit")

            validations.append(
                PermitValidation(
                    incident_id=incident_id,
                    evidence_id=item.evidence_id,
                    document_type=metadata.get("document_type", "permit_to_work"),
                    is_valid=not issues,
                    permit_number=metadata.get("permit_number"),
                    work_type=metadata.get("work_type"),
                    expiry_at=expiry_at,
                    issues=sorted(set(issues)),
                    extracted_fields=metadata,
                    model_version=self.model_version,
                )
            )
        return validations

    def _metadata_for(self, item: EvidenceRef) -> dict:
        if not self.blob_reader or not self.extractor:
            return item.metadata
        if not item.uri.startswith("blob://"):
            return item.metadata

        document_bytes = self.blob_reader.read(item.uri)
        extracted = self.extractor.extract(document_bytes)
        return {**extracted, **item.metadata}

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            return None
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
