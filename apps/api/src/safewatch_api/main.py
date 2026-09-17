from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from safewatch_api.config import get_settings
from safewatch_api.orchestrator import SafeWatchOrchestrator
from safewatch_api.repositories import build_incident_repository
from safewatch_api.schemas import (
    AnalyzeIncidentRequest,
    EvidenceUploadResponse,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    WorkflowResult,
)
from safewatch_api.services.blob_storage import AzureBlobWriter
from safewatch_api.services.document_intelligence import AzureDocumentIntelligenceExtractor
from safewatch_contracts.models import AuditEvent, IncidentRecord, IncidentStatus

app = FastAPI(title="SafeWatch AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
settings = get_settings()
repository = build_incident_repository(settings)
orchestrator = SafeWatchOrchestrator(settings, repository)
blob_writer = AzureBlobWriter(settings.storage_account_name) if settings.storage_account_name else None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "safewatch-api"}


@app.get("/config/status")
def config_status() -> dict[str, bool | str]:
    return {
        "environment": settings.environment,
        "cosmos_configured": settings.cosmos_endpoint is not None,
        "storage_account_configured": settings.storage_account_name is not None,
        "azure_ai_vision_configured": settings.azure_ai_vision_endpoint is not None,
        "document_intelligence_configured": settings.document_intelligence_endpoint is not None,
        "azure_ai_search_configured": settings.azure_ai_search_endpoint is not None,
        "azure_openai_configured": settings.azure_openai_endpoint is not None,
        "azure_openai_api_key_configured": settings.azure_openai_api_key is not None,
        "application_insights_configured": settings.applicationinsights_connection_string is not None,
        "langsmith_tracing_enabled": settings.langsmith_tracing,
        "langsmith_configured": settings.langsmith_api_key is not None,
        "langsmith_project": settings.langsmith_project,
        "vision_model_version": settings.vision_model_version,
        "document_model_version": settings.document_model_version,
        "document_intelligence_model_id": settings.document_intelligence_model_id,
        "document_parser_version": AzureDocumentIntelligenceExtractor.parser_version,
        "azure_ai_search_index_name": settings.azure_ai_search_index_name,
    }


@app.post("/incidents/analyze", response_model=WorkflowResult)
def analyze_incident(request: AnalyzeIncidentRequest) -> WorkflowResult:
    return orchestrator.analyze(request)


@app.post("/evidence/upload", response_model=EvidenceUploadResponse)
async def upload_evidence(
    kind: str = Form(...),
    evidence_id: str = Form(...),
    file: UploadFile = File(...),
) -> EvidenceUploadResponse:
    if kind not in {"image", "permit", "document"}:
        raise HTTPException(status_code=400, detail="kind must be image, permit, or document")
    if blob_writer is None:
        raise HTTPException(status_code=503, detail="Blob storage is not configured")

    container = "evidence-images" if kind == "image" else "evidence-documents"
    content = await file.read()
    uri = blob_writer.upload(container, file.filename or evidence_id, content, file.content_type)
    return EvidenceUploadResponse(
        evidence_id=evidence_id,
        uri=uri,
        kind=kind,
        filename=file.filename or evidence_id,
        content_type=file.content_type,
    )


@app.get("/incidents/{incident_id}/records")
def incident_records(incident_id: str) -> list[dict]:
    return repository.list_by_incident(incident_id)


@app.post("/incidents/{incident_id}/review", response_model=ReviewDecisionResponse)
def review_incident(incident_id: str, request: ReviewDecisionRequest) -> ReviewDecisionResponse:
    existing = repository.get_incident(incident_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Incident was not found")
    if existing.get("status") != IncidentStatus.PENDING_REVIEW:
        raise HTTPException(status_code=409, detail="Only pending review incidents can be approved or rejected")

    status = IncidentStatus.APPROVED if request.action == "approve" else IncidentStatus.REJECTED
    updated = IncidentRecord(
        incident_id=existing["incident_id"],
        site_id=existing["site_id"],
        zone_id=existing.get("zone_id"),
        work_type=existing.get("work_type"),
        contractor_id=existing.get("contractor_id"),
        status=status,
        evidence_ids=existing.get("evidence_ids", []),
        agent_run_ids=existing.get("agent_run_ids", []),
        created_by=existing["created_by"],
        created_at=datetime.fromisoformat(existing["created_at"].replace("Z", "+00:00")),
        updated_at=datetime.now(timezone.utc),
    )
    repository.save_item(updated, "incident")
    repository.save_item(
        AuditEvent(
            incident_id=incident_id,
            correlation_id=f"review-{uuid4()}",
            event_type=f"incident_{status}",
            actor_type="user",
            actor_id=request.reviewer_id,
            payload={"comment": request.comment},
        ),
        "audit_event",
    )
    return ReviewDecisionResponse(
        incident_id=incident_id,
        status=status,
        reviewer_id=request.reviewer_id,
        comment=request.comment,
    )
