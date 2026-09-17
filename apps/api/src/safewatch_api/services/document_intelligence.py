from io import BytesIO
import re
from typing import Any


class AzureDocumentIntelligenceExtractor:
    parser_version = "permit-parser-v2"

    def __init__(self, endpoint: str, model_id: str = "prebuilt-layout") -> None:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.identity import DefaultAzureCredential

        self.model_id = model_id
        self.client = DocumentIntelligenceClient(endpoint=endpoint, credential=DefaultAzureCredential())

    def extract(self, document_bytes: bytes) -> dict[str, Any]:
        poller = self._begin_analyze(document_bytes)
        result = poller.result()
        content = getattr(result, "content", "") or ""
        fields = self._key_value_pairs(result)
        inferred = self._infer_fields_from_text(content)
        fields.update(inferred)
        permit_number = fields.get("permit_number")
        if permit_number:
            fields["permit_number"] = normalize_permit_number(permit_number)
        if not is_valid_permit_number(fields.get("permit_number")):
            fields.pop("permit_number", None)
        fields["content_preview"] = content[:1200]
        return fields

    def _begin_analyze(self, document_bytes: bytes) -> Any:
        body = BytesIO(document_bytes)
        if self.model_id == "prebuilt-layout":
            try:
                from azure.ai.documentintelligence.models import DocumentAnalysisFeature

                return self.client.begin_analyze_document(
                    self.model_id,
                    body=body,
                    features=[DocumentAnalysisFeature.KEY_VALUE_PAIRS],
                )
            except (ImportError, TypeError, AttributeError):
                body.seek(0)
        return self.client.begin_analyze_document(self.model_id, body=body)

    @staticmethod
    def _key_value_pairs(result: Any) -> dict[str, str]:
        fields: dict[str, str] = {}
        for pair in getattr(result, "key_value_pairs", []) or []:
            key = getattr(getattr(pair, "key", None), "content", None)
            value = getattr(getattr(pair, "value", None), "content", None)
            if key and value:
                fields[normalize_field_name(key)] = value
        return fields

    @staticmethod
    def _infer_fields_from_text(content: str) -> dict[str, str]:
        inferred: dict[str, str] = {}
        permit_match = re.search(r"\b(PTW[-\s#:]*[A-Z0-9]{3,})\b", content, re.IGNORECASE)
        if permit_match:
            inferred["permit_number"] = normalize_permit_number(permit_match.group(1))

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        for index, line in enumerate(lines):
            lowered_line = line.lower()
            next_line = lines[index + 1] if index + 1 < len(lines) else ""
            inline_permit = re.search(r"permit\s+number\s*[:#-]?\s*([A-Z0-9-]+)", line, re.IGNORECASE)
            if inline_permit and is_valid_permit_number(inline_permit.group(1)):
                inferred["permit_number"] = normalize_permit_number(inline_permit.group(1))
            elif lowered_line == "permit number" and next_line and is_valid_permit_number(next_line):
                inferred["permit_number"] = normalize_permit_number(next_line)
            elif lowered_line == "work type" and next_line:
                inferred["work_type"] = normalize_value(next_line)
            elif lowered_line == "status" and next_line:
                inferred["status"] = next_line.lower()
            elif lowered_line == "expiry at" and next_line:
                inferred["expiry_at"] = next_line

        lowered = content.lower()
        if "expired" in lowered:
            inferred["status"] = "expired"
        elif ("valid" in lowered or "approved" in lowered) and "status" not in inferred:
            inferred["status"] = "valid"

        if ("work at height" in lowered or "working at height" in lowered) and "work_type" not in inferred:
            inferred["work_type"] = "work_at_height"

        return inferred


def normalize_field_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def normalize_value(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def normalize_permit_number(value: str) -> str:
    candidate = value.strip().upper()
    candidate = re.sub(r"[^A-Z0-9-]+", "-", candidate).strip("-")
    if candidate.startswith("PTW") and not candidate.startswith("PTW-"):
        suffix = candidate.removeprefix("PTW").strip("-")
        return f"PTW-{suffix}" if suffix else "PTW"
    return candidate


def is_valid_permit_number(value: str | None) -> bool:
    if not value:
        return False
    return re.fullmatch(r"PTW-\d{3,}", normalize_permit_number(value)) is not None
