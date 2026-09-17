from uuid import uuid4

from safewatch_api.agents import (
    ComplianceRagAgent,
    DocumentAgent,
    GovernanceAgent,
    ReportAgent,
    RiskScoringAgent,
    VisionAgent,
)
from safewatch_api.config import Settings
from safewatch_api.graph import WorkflowAgents, WorkflowRuntime, build_workflow
from safewatch_api.repositories.incidents import IncidentRepository
from safewatch_api.schemas import AnalyzeIncidentRequest, WorkflowResult
from safewatch_api.services.azure_openai_embeddings import AzureOpenAIEmbeddingClient
from safewatch_api.services.azure_search import AzureRegulationSearchClient
from safewatch_api.services.azure_vision import AzureVisionImageAnalyzer
from safewatch_api.services.blob_storage import AzureBlobReader
from safewatch_api.services.document_intelligence import AzureDocumentIntelligenceExtractor
from safewatch_api.services.retry import RetryPolicy
from safewatch_api.services.telemetry import Telemetry


class SafeWatchOrchestrator:
    def __init__(self, settings: Settings, repository: IncidentRepository, telemetry: Telemetry | None = None) -> None:
        self.settings = settings
        self.repository = repository
        self.telemetry = telemetry or Telemetry()
        self.retry_policy = RetryPolicy()
        self.vision_agent = self._build_vision_agent(settings)
        self.document_agent = self._build_document_agent(settings)
        self.rag_agent = self._build_rag_agent(settings)
        self.risk_agent = RiskScoringAgent(settings.risk_policy_version)
        self.governance_agent = GovernanceAgent(settings.policy_version)
        self.report_agent = ReportAgent()
        runtime = WorkflowRuntime(
            agents=WorkflowAgents(
                self.vision_agent,
                self.document_agent,
                self.rag_agent,
                self.risk_agent,
                self.governance_agent,
                self.report_agent,
            ),
            repository=self.repository,
            telemetry=self.telemetry,
            retry_policy=self.retry_policy,
            versions={
                "vision_model_version": settings.vision_model_version,
                "document_model_version": settings.document_model_version,
                "chat_deployment": settings.azure_openai_chat_deployment,
                "prompt_version": settings.prompt_version,
                "risk_policy_version": settings.risk_policy_version,
                "policy_version": settings.policy_version,
            },
        )
        self.graph = build_workflow(runtime)

    @staticmethod
    def _build_vision_agent(settings: Settings) -> VisionAgent:
        if settings.storage_account_name and settings.azure_ai_vision_endpoint:
            return VisionAgent(
                settings.vision_model_version,
                blob_reader=AzureBlobReader(settings.storage_account_name),
                analyzer=AzureVisionImageAnalyzer(
                    settings.azure_ai_vision_endpoint,
                    settings.azure_ai_vision_api_version,
                    settings.azure_ai_vision_api_key,
                ),
            )
        return VisionAgent(settings.vision_model_version)

    @staticmethod
    def _build_document_agent(settings: Settings) -> DocumentAgent:
        if settings.storage_account_name and settings.document_intelligence_endpoint:
            return DocumentAgent(
                settings.document_model_version,
                blob_reader=AzureBlobReader(settings.storage_account_name),
                extractor=AzureDocumentIntelligenceExtractor(
                    settings.document_intelligence_endpoint,
                    settings.document_intelligence_model_id,
                ),
            )
        return DocumentAgent(settings.document_model_version)

    @staticmethod
    def _build_rag_agent(settings: Settings) -> ComplianceRagAgent:
        if settings.azure_ai_search_endpoint and settings.azure_openai_endpoint:
            embedding_client = AzureOpenAIEmbeddingClient(
                settings.azure_openai_endpoint,
                settings.azure_openai_embedding_deployment,
                settings.azure_openai_embedding_api_version,
                settings.azure_openai_api_key,
            )
            search_client = AzureRegulationSearchClient(
                settings.azure_ai_search_endpoint,
                settings.azure_ai_search_index_name,
                embedding_client,
                settings.rag_index_version,
                settings.azure_ai_search_api_version,
            )
            return ComplianceRagAgent(settings.rag_index_version, search_client=search_client)
        return ComplianceRagAgent(settings.rag_index_version)

    def analyze(self, request: AnalyzeIncidentRequest) -> WorkflowResult:
        correlation_id = f"corr-{uuid4()}"
        final_state = self.graph.invoke({"request": request, "correlation_id": correlation_id})

        return WorkflowResult(
            incident=final_state["incident"],
            detections=final_state["detections"],
            permit_validations=final_state["permit_validations"],
            citations=final_state["citations"],
            risk=final_state["risk"],
            governance=final_state["governance"],
            reviewer_packet=final_state["reviewer_packet"],
        )
