import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "contracts" / "src"))
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

from safewatch_api.config import Settings  # noqa: E402
from safewatch_api.agents.document import DocumentAgent  # noqa: E402
from safewatch_api.agents.rag import ComplianceRagAgent  # noqa: E402
from safewatch_api.agents.rag import build_regulation_query  # noqa: E402
from safewatch_api.agents.vision import VisionAgent  # noqa: E402
from safewatch_api.graph import SequentialWorkflow  # noqa: E402
from safewatch_api.orchestrator import SafeWatchOrchestrator  # noqa: E402
from safewatch_api.repositories.factory import build_incident_repository  # noqa: E402
from safewatch_api.repositories.incidents import document_id_for  # noqa: E402
from safewatch_api.repositories.incidents import InMemoryIncidentRepository  # noqa: E402
from safewatch_api.schemas import AnalyzeIncidentRequest, EvidenceRef  # noqa: E402
from safewatch_api.services.document_intelligence import AzureDocumentIntelligenceExtractor  # noqa: E402
from safewatch_api.services.document_intelligence import is_valid_permit_number  # noqa: E402
from safewatch_api.services.azure_vision import AzureVisionImageAnalyzer  # noqa: E402
from safewatch_api.services.retry import RetryPolicy  # noqa: E402
from safewatch_contracts.models import ApprovalLevel, Detection, IncidentStatus, RegulationCitation, RiskBand  # noqa: E402
from safewatch_contracts.models import ViolationSeverity  # noqa: E402


class Phase2WorkflowTests(unittest.TestCase):
    def test_vision_agent_reads_blob_and_uses_image_analysis(self) -> None:
        class FakeBlobReader:
            def read(self, uri: str) -> bytes:
                self.uri = uri
                return b"fake image bytes"

        class FakeAnalysis:
            text = "worker on scaffold with no harness"
            confidence = 0.93

        class FakeAnalyzer:
            def analyze(self, image_bytes: bytes) -> FakeAnalysis:
                self.image_bytes = image_bytes
                return FakeAnalysis()

        blob_reader = FakeBlobReader()
        analyzer = FakeAnalyzer()
        agent = VisionAgent("azure-ai-vision-v1", blob_reader=blob_reader, analyzer=analyzer)

        detections = agent.analyze(
            "inc-vision",
            [
                EvidenceRef(
                    evidence_id="img-1",
                    uri="blob://evidence-images/site-check.jpg",
                    kind="image",
                    metadata={"worker_count": 1},
                )
            ],
        )

        self.assertEqual(blob_reader.uri, "blob://evidence-images/site-check.jpg")
        self.assertEqual(analyzer.image_bytes, b"fake image bytes")
        self.assertEqual(detections[0].violation_type, "missing_harness_at_height")
        self.assertEqual(detections[0].severity, ViolationSeverity.CRITICAL)
        self.assertEqual(detections[0].model_version, "azure-ai-vision-v1")

    def test_azure_vision_retries_when_caption_is_not_supported_in_region(self) -> None:
        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"tagsResult":{"values":[{"name":"scaffold","confidence":0.91}]}}'

        calls: list[str] = []

        def fake_urlopen(request, timeout: int) -> FakeResponse:
            calls.append(request.full_url)
            if len(calls) == 1:
                raise HTTPError(
                    request.full_url,
                    400,
                    "Bad Request",
                    {},
                    BytesIO(b'{"error":{"message":"The feature Caption is not supported in this region."}}'),
                )
            return FakeResponse()

        analyzer = AzureVisionImageAnalyzer("https://vision.example.com", api_key="test-key")

        with patch("safewatch_api.services.azure_vision.urlopen", fake_urlopen):
            result = analyzer.analyze(b"image-bytes")

        self.assertEqual(len(calls), 2)
        self.assertIn("caption%2CdenseCaptions", calls[0])
        self.assertIn("tags%2Cobjects%2Cread%2Cpeople", calls[1])
        self.assertEqual(result.text, "scaffold")
        self.assertEqual(result.confidence, 0.91)

    def test_document_intelligence_text_inference_extracts_demo_permit_fields(self) -> None:
        fields = AzureDocumentIntelligenceExtractor._infer_fields_from_text(
            "\n".join(
                [
                    "SafeWatch AI Demo Permit",
                    "Permit-to-work document for validating the Phase 2 Document Agent.",
                    "Permit Details",
                    "Permit Number",
                    "PTW-001",
                    "Work Type",
                    "Work at Height",
                    "Status",
                    "Valid",
                    "Expiry At",
                    "2026-12-31T18:00:00Z",
                ]
            )
        )

        self.assertEqual(fields["permit_number"], "PTW-001")
        self.assertEqual(fields["work_type"], "work_at_height")
        self.assertEqual(fields["status"], "valid")
        self.assertEqual(fields["expiry_at"], "2026-12-31T18:00:00Z")
        self.assertTrue(is_valid_permit_number(fields["permit_number"]))
        self.assertFalse(is_valid_permit_number("PERMIT-TO-WORK"))

    def test_document_agent_reads_blob_and_merges_extracted_fields(self) -> None:
        class FakeBlobReader:
            def read(self, uri: str) -> bytes:
                self.uri = uri
                return b"fake pdf bytes"

        class FakeExtractor:
            def extract(self, document_bytes: bytes) -> dict:
                self.document_bytes = document_bytes
                return {
                    "permit_number": "PTW-777",
                    "document_type": "permit_to_work",
                    "work_type": "work_at_height",
                    "status": "valid",
                }

        blob_reader = FakeBlobReader()
        extractor = FakeExtractor()
        agent = DocumentAgent("azure-document-intelligence-v1", blob_reader=blob_reader, extractor=extractor)

        validations = agent.validate(
            "inc-docintel",
            [EvidenceRef(evidence_id="permit-1", uri="blob://evidence-documents/permit.pdf", kind="permit")],
        )

        self.assertEqual(blob_reader.uri, "blob://evidence-documents/permit.pdf")
        self.assertEqual(extractor.document_bytes, b"fake pdf bytes")
        self.assertEqual(validations[0].permit_number, "PTW-777")
        self.assertTrue(validations[0].is_valid)
        self.assertEqual(validations[0].model_version, "azure-document-intelligence-v1")

    def test_rag_query_uses_agent_outputs(self) -> None:
        query = build_regulation_query(
            [
                Detection(
                    incident_id="inc-rag",
                    evidence_id="img-1",
                    worker_count=1,
                    violation_type="missing_harness_at_height",
                    severity=ViolationSeverity.CRITICAL,
                    confidence=0.91,
                    model_version="mock-vision-v1",
                )
            ],
            [],
        )

        self.assertIn("missing harness at height", query)
        self.assertIn("critical ppe violation", query)

    def test_rag_agent_prefers_search_client_results(self) -> None:
        class FakeSearchClient:
            def search(self, query: str, top: int = 5) -> list[RegulationCitation]:
                self.query = query
                self.top = top
                return [
                    RegulationCitation(
                        source="OSHAD",
                        clause_id="Work-at-height",
                        title="Fall protection and access control",
                        excerpt="Workers exposed to a fall hazard should wear a full body harness.",
                        relevance_score=0.93,
                        index_version="rag-index-v1",
                    )
                ]

        search_client = FakeSearchClient()
        agent = ComplianceRagAgent("rag-index-v1", search_client=search_client)
        citations = agent.retrieve(
            [
                Detection(
                    incident_id="inc-rag",
                    evidence_id="img-1",
                    worker_count=1,
                    violation_type="missing_harness_at_height",
                    severity=ViolationSeverity.CRITICAL,
                    confidence=0.91,
                    model_version="mock-vision-v1",
                )
            ],
            [],
        )

        self.assertEqual(search_client.top, 5)
        self.assertIn("missing harness at height", search_client.query)
        self.assertEqual(citations[0].source, "OSHAD")
        self.assertEqual(citations[0].clause_id, "Work-at-height")

    def test_local_settings_use_in_memory_repository(self) -> None:
        repository = build_incident_repository(Settings(cosmos_endpoint=None))

        self.assertIsInstance(repository, InMemoryIncidentRepository)

    def test_single_cosmos_container_uses_distinct_document_ids(self) -> None:
        incident_id = "inc-001"

        ids = {
            document_id_for({"incident_id": incident_id}, "incident"),
            document_id_for({"incident_id": incident_id}, "risk_assessment"),
            document_id_for({"incident_id": incident_id}, "governance_decision"),
            document_id_for({"incident_id": incident_id}, "reviewer_packet"),
            document_id_for({"incident_id": incident_id, "agent_run_id": "run-001"}, "agent_run"),
        }

        self.assertEqual(len(ids), 5)

    def test_orchestrator_owns_compiled_workflow(self) -> None:
        repository = InMemoryIncidentRepository()
        orchestrator = SafeWatchOrchestrator(Settings(), repository)

        self.assertTrue(hasattr(orchestrator.graph, "invoke"))

    def test_low_risk_incident_auto_logs(self) -> None:
        repository = InMemoryIncidentRepository()
        orchestrator = SafeWatchOrchestrator(Settings(), repository)

        result = orchestrator.analyze(
            AnalyzeIncidentRequest(
                incident_id="inc-low",
                site_id="site-001",
                created_by="ashifa",
                evidence=[EvidenceRef(evidence_id="img-1", uri="blob://evidence-images/normal.jpg", kind="image")],
            )
        )

        self.assertEqual(result.risk.risk_band, RiskBand.LOW)
        self.assertEqual(result.governance.approval_level, ApprovalLevel.AUTO_LOG)
        self.assertEqual(result.incident.status, IncidentStatus.AUTO_LOGGED)

    def test_critical_harness_violation_escalates(self) -> None:
        repository = InMemoryIncidentRepository()
        orchestrator = SafeWatchOrchestrator(Settings(), repository)

        result = orchestrator.analyze(
            AnalyzeIncidentRequest(
                incident_id="inc-critical",
                site_id="site-001",
                zone_id="zone-04",
                created_by="ashifa",
                evidence=[
                    EvidenceRef(
                        evidence_id="img-1",
                        uri="blob://evidence-images/scaffold-missing_harness.jpg",
                        kind="image",
                        metadata={"worker_count": 1},
                    )
                ],
            )
        )

        self.assertEqual(result.risk.risk_band, RiskBand.HIGH)
        self.assertEqual(result.governance.approval_level, ApprovalLevel.ESCALATION_COMMITTEE)
        self.assertIn("critical_ppe_violation", result.governance.hard_overrides)
        self.assertEqual(result.incident.status, IncidentStatus.PENDING_REVIEW)

    def test_expired_permit_blocks_closure_and_routes_to_hse(self) -> None:
        repository = InMemoryIncidentRepository()
        orchestrator = SafeWatchOrchestrator(Settings(), repository)

        result = orchestrator.analyze(
            AnalyzeIncidentRequest(
                incident_id="inc-expired-permit",
                site_id="site-001",
                created_by="ashifa",
                evidence=[
                    EvidenceRef(
                        evidence_id="permit-1",
                        uri="blob://evidence-documents/permit.pdf",
                        kind="permit",
                        metadata={"permit_number": "PTW-001", "status": "expired"},
                    )
                ],
            )
        )

        self.assertEqual(result.governance.approval_level, ApprovalLevel.HSE_MANAGER)
        self.assertIn("expired_permit", result.governance.hard_overrides)
        self.assertIn("close_incident_without_hse_review", result.governance.blocked_actions)

    def test_missing_permit_number_routes_to_hse_review(self) -> None:
        repository = InMemoryIncidentRepository()
        orchestrator = SafeWatchOrchestrator(Settings(), repository)

        result = orchestrator.analyze(
            AnalyzeIncidentRequest(
                incident_id="inc-missing-permit-number",
                site_id="site-001",
                created_by="ashifa",
                evidence=[
                    EvidenceRef(
                        evidence_id="permit-1",
                        uri="blob://evidence-documents/missing-permit-number.pdf",
                        kind="permit",
                        metadata={"document_type": "permit_to_work", "work_type": "work_at_height"},
                    )
                ],
            )
        )

        self.assertEqual(result.risk.risk_score, 20)
        self.assertEqual(result.governance.approval_level, ApprovalLevel.HSE_MANAGER)
        self.assertTrue(result.governance.human_review_required)
        self.assertIn("missing_permit_number", result.governance.hard_overrides)
        self.assertEqual(result.incident.status, IncidentStatus.PENDING_REVIEW)

    def test_retry_policy_retries_transient_failures(self) -> None:
        attempts = {"count": 0}

        def flaky_call() -> str:
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("temporary service failure")
            return "ok"

        result = RetryPolicy(attempts=2, delay_seconds=0).run(flaky_call)

        self.assertEqual(result, "ok")
        self.assertEqual(attempts["count"], 2)

    def test_local_fallback_keeps_tests_running_without_langgraph_package(self) -> None:
        repository = InMemoryIncidentRepository()
        orchestrator = SafeWatchOrchestrator(Settings(), repository)

        if isinstance(orchestrator.graph, SequentialWorkflow):
            self.assertTrue(hasattr(orchestrator.graph, "invoke"))


if __name__ == "__main__":
    unittest.main()
