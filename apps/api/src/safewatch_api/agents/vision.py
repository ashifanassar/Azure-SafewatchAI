from typing import Protocol

from safewatch_api.schemas import EvidenceRef
from safewatch_contracts.models import Detection, ViolationSeverity


class BlobReader(Protocol):
    def read(self, uri: str) -> bytes:
        ...


class ImageAnalysis(Protocol):
    text: str
    confidence: float


class ImageAnalyzer(Protocol):
    def analyze(self, image_bytes: bytes) -> ImageAnalysis:
        ...


class VisionAgent:
    def __init__(
        self,
        model_version: str,
        blob_reader: BlobReader | None = None,
        analyzer: ImageAnalyzer | None = None,
    ) -> None:
        self.model_version = model_version
        self.blob_reader = blob_reader
        self.analyzer = analyzer

    def analyze(self, incident_id: str, evidence: list[EvidenceRef]) -> list[Detection]:
        detections: list[Detection] = []
        for item in evidence:
            if item.kind != "image":
                continue

            text, analysis_confidence = self._image_signals(item)
            at_height = any(term in text for term in ["height", "scaffold", "roof", "ladder", "elevated", "fall"])
            missing_harness = any(
                term in text for term in ["missing_harness", "missing harness", "no harness", "without harness"]
            )
            missing_helmet = any(
                term in text for term in ["missing_helmet", "missing helmet", "no helmet", "without helmet", "no hard hat"]
            )

            if at_height and missing_harness:
                detections.append(
                    Detection(
                        incident_id=incident_id,
                        evidence_id=item.evidence_id,
                        worker_count=int(item.metadata.get("worker_count", 1)),
                        violation_type="missing_harness_at_height",
                        severity=ViolationSeverity.CRITICAL,
                        confidence=max(analysis_confidence, 0.91),
                        model_version=self.model_version,
                    )
                )
            elif missing_helmet:
                detections.append(
                    Detection(
                        incident_id=incident_id,
                        evidence_id=item.evidence_id,
                        worker_count=int(item.metadata.get("worker_count", 1)),
                        violation_type="missing_helmet",
                        severity=ViolationSeverity.MEDIUM,
                        confidence=max(analysis_confidence, 0.84),
                        model_version=self.model_version,
                    )
                )
            else:
                detections.append(
                    Detection(
                        incident_id=incident_id,
                        evidence_id=item.evidence_id,
                        worker_count=int(item.metadata.get("worker_count", 0)),
                        severity=ViolationSeverity.LOW,
                        confidence=max(analysis_confidence, 0.75),
                        model_version=self.model_version,
                    )
                )
        return detections

    def _image_signals(self, item: EvidenceRef) -> tuple[str, float]:
        parts = [item.uri, str(item.metadata)]
        confidence = 0.0
        if self.blob_reader and self.analyzer and item.uri.startswith("blob://"):
            image_bytes = self.blob_reader.read(item.uri)
            analysis = self.analyzer.analyze(image_bytes)
            parts.append(analysis.text)
            confidence = analysis.confidence
        return " ".join(parts).lower(), confidence
