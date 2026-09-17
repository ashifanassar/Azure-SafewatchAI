from datetime import datetime, timezone
from typing import Callable, NotRequired, Protocol, TypedDict

from safewatch_api.agents import (
    ComplianceRagAgent,
    DocumentAgent,
    GovernanceAgent,
    ReportAgent,
    RiskScoringAgent,
    VisionAgent,
)
from safewatch_api.repositories.incidents import IncidentRepository
from safewatch_api.schemas import AnalyzeIncidentRequest, ReviewerPacket
from safewatch_api.services.retry import RetryPolicy
from safewatch_api.services.telemetry import Telemetry
from safewatch_contracts.models import (
    AgentRun,
    AuditEvent,
    Detection,
    GovernanceDecision,
    IncidentRecord,
    IncidentStatus,
    PermitValidation,
    RegulationCitation,
    RiskAssessment,
)

try:
    from langgraph.graph import END, StateGraph
except ModuleNotFoundError:
    END = "__end__"
    StateGraph = None


class CompiledWorkflow(Protocol):
    def invoke(self, state: "WorkflowState") -> "WorkflowState":
        ...


class WorkflowState(TypedDict):
    request: AnalyzeIncidentRequest
    correlation_id: str
    incident: NotRequired[IncidentRecord]
    detections: NotRequired[list[Detection]]
    permit_validations: NotRequired[list[PermitValidation]]
    citations: NotRequired[list[RegulationCitation]]
    risk: NotRequired[RiskAssessment]
    governance: NotRequired[GovernanceDecision]
    reviewer_packet: NotRequired[ReviewerPacket]


class WorkflowAgents:
    def __init__(
        self,
        vision_agent: VisionAgent,
        document_agent: DocumentAgent,
        rag_agent: ComplianceRagAgent,
        risk_agent: RiskScoringAgent,
        governance_agent: GovernanceAgent,
        report_agent: ReportAgent,
    ) -> None:
        self.vision_agent = vision_agent
        self.document_agent = document_agent
        self.rag_agent = rag_agent
        self.risk_agent = risk_agent
        self.governance_agent = governance_agent
        self.report_agent = report_agent


class WorkflowRuntime:
    def __init__(
        self,
        agents: WorkflowAgents,
        repository: IncidentRepository,
        telemetry: Telemetry,
        retry_policy: RetryPolicy,
        versions: dict[str, str],
    ) -> None:
        self.agents = agents
        self.repository = repository
        self.telemetry = telemetry
        self.retry_policy = retry_policy
        self.versions = versions

    def create_incident(self, state: WorkflowState) -> WorkflowState:
        request = state["request"]
        incident = IncidentRecord(
            incident_id=request.incident_id,
            site_id=request.site_id,
            zone_id=request.zone_id,
            work_type=request.work_type,
            contractor_id=request.contractor_id,
            status=IncidentStatus.ANALYZING,
            evidence_ids=[item.evidence_id for item in request.evidence],
            created_by=request.created_by,
        )
        self.repository.save_item(incident, "incident")
        self.audit(
            request.incident_id,
            state["correlation_id"],
            "incident_analysis_started",
            {"evidence_count": len(request.evidence)},
        )
        return {**state, "incident": incident}

    def run_vision(self, state: WorkflowState) -> WorkflowState:
        request = state["request"]
        detections = self.run_agent(
            "vision-agent",
            request.incident_id,
            state["correlation_id"],
            lambda: self.agents.vision_agent.analyze(request.incident_id, request.evidence),
            model_version=self.versions["vision_model_version"],
        )
        return {**state, "detections": detections}

    def run_document(self, state: WorkflowState) -> WorkflowState:
        request = state["request"]
        validations = self.run_agent(
            "document-agent",
            request.incident_id,
            state["correlation_id"],
            lambda: self.agents.document_agent.validate(request.incident_id, request.evidence),
            model_version=self.versions["document_model_version"],
        )
        return {**state, "permit_validations": validations}

    def run_rag(self, state: WorkflowState) -> WorkflowState:
        request = state["request"]
        citations = self.run_agent(
            "compliance-rag-agent",
            request.incident_id,
            state["correlation_id"],
            lambda: self.agents.rag_agent.retrieve(state["detections"], state["permit_validations"]),
            model_version=self.versions["chat_deployment"],
            prompt_version=self.versions["prompt_version"],
        )
        return {**state, "citations": citations}

    def run_risk(self, state: WorkflowState) -> WorkflowState:
        request = state["request"]
        risk = self.run_agent(
            "risk-scoring-agent",
            request.incident_id,
            state["correlation_id"],
            lambda: self.agents.risk_agent.assess(
                request.incident_id,
                state["detections"],
                state["permit_validations"],
                request.contractor_id,
            ),
            policy_version=self.versions["risk_policy_version"],
        )
        return {**state, "risk": risk}

    def run_governance(self, state: WorkflowState) -> WorkflowState:
        request = state["request"]
        governance = self.run_agent(
            "governance-agent",
            request.incident_id,
            state["correlation_id"],
            lambda: self.agents.governance_agent.decide(
                state["risk"],
                state["detections"],
                state["permit_validations"],
                request.contractor_id,
            ),
            policy_version=self.versions["policy_version"],
        )
        return {**state, "governance": governance}

    def run_report(self, state: WorkflowState) -> WorkflowState:
        request = state["request"]
        packet = self.run_agent(
            "report-agent",
            request.incident_id,
            state["correlation_id"],
            lambda: self.agents.report_agent.build_packet(
                request.incident_id,
                state["detections"],
                state["permit_validations"],
                state["citations"],
                state["governance"],
            ),
            prompt_version=self.versions["prompt_version"],
        )
        return {**state, "reviewer_packet": packet}

    def persist_outputs(self, state: WorkflowState) -> WorkflowState:
        incident = state["incident"]
        governance = state["governance"]
        incident.status = IncidentStatus.PENDING_REVIEW if governance.human_review_required else IncidentStatus.AUTO_LOGGED
        incident.updated_at = datetime.now(timezone.utc)
        self.repository.save_item(incident, "incident")
        self.repository.save_item(state["risk"], "risk_assessment")
        self.repository.save_item(governance, "governance_decision")
        self.repository.save_item(state["reviewer_packet"], "reviewer_packet")
        self.audit(
            incident.incident_id,
            state["correlation_id"],
            "governance_decision_recorded",
            {"approval_level": governance.approval_level, "policy_version": governance.policy_version},
        )
        return state

    def run_agent(
        self,
        agent_name: str,
        incident_id: str,
        correlation_id: str,
        fn: Callable,
        model_version: str | None = None,
        prompt_version: str | None = None,
        policy_version: str | None = None,
    ):
        run = AgentRun(
            agent_run_id=f"run-{correlation_id}-{agent_name}",
            incident_id=incident_id,
            agent_name=agent_name,
            correlation_id=correlation_id,
            status="started",
            model_version=model_version,
            prompt_version=prompt_version,
            policy_version=policy_version,
        )
        self.repository.save_item(run, "agent_run")
        try:
            with self.telemetry.trace(agent_name, incident_id=incident_id, correlation_id=correlation_id):
                output = self.retry_policy.run(fn)
            self.repository.save_item(
                run.model_copy(update={"status": "succeeded", "completed_at": datetime.now(timezone.utc)}),
                "agent_run",
            )
            return output
        except Exception as exc:
            self.repository.save_item(
                run.model_copy(
                    update={
                        "status": "failed",
                        "completed_at": datetime.now(timezone.utc),
                        "error_message": str(exc),
                    }
                ),
                "agent_run",
            )
            raise

    def audit(self, incident_id: str, correlation_id: str, event_type: str, payload: dict) -> None:
        self.repository.save_item(
            AuditEvent(
                incident_id=incident_id,
                correlation_id=correlation_id,
                event_type=event_type,
                actor_type="system",
                actor_id="langgraph-orchestrator",
                payload=payload,
            ),
            "audit_event",
        )


def build_workflow(runtime: WorkflowRuntime) -> CompiledWorkflow:
    if StateGraph is None:
        return SequentialWorkflow(runtime)

    graph = StateGraph(WorkflowState)
    graph.add_node("create_incident", runtime.create_incident)
    graph.add_node("vision_agent", runtime.run_vision)
    graph.add_node("document_agent", runtime.run_document)
    graph.add_node("compliance_rag_agent", runtime.run_rag)
    graph.add_node("risk_scoring_agent", runtime.run_risk)
    graph.add_node("governance_agent", runtime.run_governance)
    graph.add_node("report_agent", runtime.run_report)
    graph.add_node("persist_outputs", runtime.persist_outputs)

    graph.set_entry_point("create_incident")
    graph.add_edge("create_incident", "vision_agent")
    graph.add_edge("vision_agent", "document_agent")
    graph.add_edge("document_agent", "compliance_rag_agent")
    graph.add_edge("compliance_rag_agent", "risk_scoring_agent")
    graph.add_edge("risk_scoring_agent", "governance_agent")
    graph.add_edge("governance_agent", "report_agent")
    graph.add_edge("report_agent", "persist_outputs")
    graph.add_edge("persist_outputs", END)
    return graph.compile()


class SequentialWorkflow:
    def __init__(self, runtime: WorkflowRuntime) -> None:
        self.runtime = runtime

    def invoke(self, state: WorkflowState) -> WorkflowState:
        for node in (
            self.runtime.create_incident,
            self.runtime.run_vision,
            self.runtime.run_document,
            self.runtime.run_rag,
            self.runtime.run_risk,
            self.runtime.run_governance,
            self.runtime.run_report,
            self.runtime.persist_outputs,
        ):
            state = node(state)
        return state
