# SafeWatch AI v1

**Problem Statement:**
High-risk site work often starts with fragmented evidence, manual permit checks, delayed HSE review, and inconsistent governance decisions. Work permits, site photos, PPE observations, and regulatory requirements are usually reviewed across disconnected tools, creating missed hazards, weak auditability, and slow escalation.

SafeWatch AI v1 is an agentic HSE governance platform built on Azure. It demonstrates how site evidence can be analyzed by multiple agents, scored for risk, checked against safety regulations, routed through deterministic governance rules, and reviewed by humans when approval is required.

The platform supports work-start safety review for scenarios such as work at height, missing permit information, missing PPE, unsafe access, and escalation-based approval workflows.

**Embedding Model Used:** Azure OpenAI embedding deployment `embed-safewatch-v1`  
**LLM Used:** Azure OpenAI chat deployment `chat-safewatch-v1`

## Architecture

```text
SafeWatch Web UI
        |
        v
Azure Front Door + WAF              [edge hardening path]
        |
        v
Azure API Management
        |
        v
Azure Container Apps - FastAPI Backend
        |
        v
LangGraph Multi-Agent Workflow
        |
        +--> Vision Agent
        |       +--> Azure AI Vision
        |
        +--> Document Agent
        |       +--> Azure Document Intelligence
        |
        +--> Compliance RAG Agent
        |       +--> Azure OpenAI embeddings
        |       +--> Azure AI Search regulation index
        |
        +--> Risk Scoring Agent
        +--> Governance Agent
        +--> Report Agent
        +--> Persist Outputs
                +--> Cosmos DB incident records and audit events
                +--> Blob Storage evidence references

Monitoring:
FastAPI / agents -> Azure Monitor + Log Analytics + Azure Workbook
LangGraph workflow -> LangSmith tracing
```


## Main Features

- Work permit PDF and site safety image intake.
- Azure Blob Storage design for raw evidence files.
- Azure AI Vision integration for PPE and work-at-height safety checks.
- Azure Document Intelligence integration for permit validation.
- Compliance RAG over ISO 45001, OSHAD, TRAKHEES, and related HSE guidance.
- Azure OpenAI embeddings and Azure AI Search for regulation retrieval.
- LangGraph multi-agent orchestration.
- Risk scoring based on permit, PPE, work-at-height, and contractor signals.
- Deterministic governance rules for auto-log, HSE manager review, and escalation committee review.
- Reviewer packet generation with risk explanation, findings, citations, and blocked actions.
- Human Review Queue with approve/reject workflow.
- Cosmos DB incident, risk, governance, reviewer packet, agent run, and audit event records.
- Azure API Management as API gateway.
- Azure Monitor, Log Analytics, and Azure Workbook monitoring.
- LangSmith tracing for the LangGraph run tree and agent latency.
- GitHub repository for source control and project documentation.

## Agent Architecture

```text
LangGraph
  -> create_incident
  -> vision_agent
  -> document_agent
  -> compliance_rag_agent
  -> risk_scoring_agent
  -> governance_agent
  -> report_agent
  -> persist_outputs
```

Agent responsibility:

- **Vision Agent:** analyzes site images for PPE, harness, helmet, scaffold, ladder, roof, elevated platform, and fall hazard signals.
- **Document Agent:** validates permit number, work type, permit status, expiry, and required approval details.
- **Compliance RAG Agent:** retrieves relevant regulatory citations from the safety knowledge base.
- **Risk Scoring Agent:** computes composite risk score and risk band.
- **Governance Agent:** applies deterministic policy rules and decides auto-log or human review.
- **Report Agent:** creates the reviewer packet used by HSE managers and escalation reviewers.
- **Persist Outputs:** stores incident records, decisions, reviewer packets, agent runs, and audit events.

## Key Endpoints

```text
GET    /health
GET    /config/status
POST   /evidence/upload
POST   /incidents/analyze
GET    /incidents/{incident_id}/records
POST   /incidents/{incident_id}/review
```

Review endpoint actions:

```json
{
  "action": "approve",
  "reviewer_id": "hse_manager",
  "comment": "Approved after review"
}
```

or:

```json
{
  "action": "reject",
  "reviewer_id": "hse_manager",
  "comment": "Rejected due to missing fall protection"
}
```

## Project Structure

```text
apps/
  api/
    Dockerfile
    requirements.txt
    src/safewatch_api/
      agents/
        document.py
        governance.py
        rag.py
        report.py
        risk.py
        vision.py
      repositories/
        cosmos.py
        factory.py
        incidents.py
      services/
        azure_openai_embeddings.py
        azure_search.py
        azure_vision.py
        blob_storage.py
        document_intelligence.py
        retry.py
        telemetry.py
      config.py
      graph.py
      main.py
      orchestrator.py
      schemas.py
  frontend/
    Dockerfile
    src/
      app.js
      index.html
      styles.css

data/
  regulations/
    safewatch_regulations.json

docs/
  adr/
  api-contracts.md
  architecture-diagram.mmd
  implementation-roadmap.md
  phase-0-1-azure-console-checklist.md
  safewatch-ai-v1-architecture.md

infra/
  bicep/
    main.bicep
    main.parameters.json

packages/
  contracts/
    src/safewatch_contracts/
      models.py

tests/
  test_blob_storage.py
  test_contracts.py
  test_phase2_workflow.py

tools/
  create_demo_permit_pdf.py
  ingest_regulations.py
```

## Environment Variables

Configure these in Azure Container Apps or local environment variables.

```text
SAFEWATCH_ENVIRONMENT=azure
SAFEWATCH_POLICY_VERSION=governance-policy-v1
SAFEWATCH_RISK_POLICY_VERSION=risk-policy-v1
SAFEWATCH_VISION_MODEL_VERSION=azure-ai-vision-v1
SAFEWATCH_DOCUMENT_MODEL_VERSION=document-intelligence-v1
SAFEWATCH_RAG_INDEX_VERSION=rag-index-v1
SAFEWATCH_PROMPT_VERSION=prompt-v1

SAFEWATCH_COSMOS_ENDPOINT=
SAFEWATCH_COSMOS_DATABASE=safewatch
SAFEWATCH_COSMOS_CONTAINER=incidents

SAFEWATCH_STORAGE_ACCOUNT_NAME=

SAFEWATCH_AZURE_AI_VISION_ENDPOINT=
SAFEWATCH_AZURE_AI_VISION_API_KEY=
SAFEWATCH_AZURE_AI_VISION_API_VERSION=2024-02-01

SAFEWATCH_DOCUMENT_INTELLIGENCE_ENDPOINT=
SAFEWATCH_DOCUMENT_INTELLIGENCE_MODEL_ID=prebuilt-layout

SAFEWATCH_AZURE_OPENAI_ENDPOINT=
SAFEWATCH_AZURE_OPENAI_API_KEY=
SAFEWATCH_AZURE_OPENAI_CHAT_DEPLOYMENT=chat-safewatch-v1
SAFEWATCH_AZURE_OPENAI_EMBEDDING_DEPLOYMENT=embed-safewatch-v1
SAFEWATCH_AZURE_OPENAI_EMBEDDING_API_VERSION=2024-02-01

SAFEWATCH_AZURE_AI_SEARCH_ENDPOINT=
SAFEWATCH_AZURE_AI_SEARCH_INDEX_NAME=safewatch-regulations-v1
SAFEWATCH_AZURE_AI_SEARCH_API_VERSION=2024-07-01

APPLICATIONINSIGHTS_CONNECTION_STRING=

LANGSMITH_TRACING=true
LANGSMITH_PROJECT=safewatch-ai-v1
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=
LANGSMITH_WORKSPACE_ID=
```

## Local Run

Install dependencies:

```powershell
pip install -e .
pip install -r apps/api/requirements.txt
```

Run API:

```powershell
uvicorn safewatch_api.main:app --reload --port 8000
```

Health check:

```powershell
curl http://localhost:8000/health
```

Run tests:

```powershell
python -m unittest discover -s tests
```

## Docker Build

Build backend:

```powershell
docker build -f apps/api/Dockerfile -t safewatch-api:local .
```

Run backend:

```powershell
docker run --rm -p 8000:8000 safewatch-api:local
```

Build frontend:

```powershell
docker build -f apps/frontend/Dockerfile -t safewatch-ui:local .
```

The v1 frontend is a lightweight static UI, not a Next.js application.

## Azure Deployment

Current Azure deployment uses:

```text
Resource group: rg-safewatch-v1-uaenorth
Backend Container App: safewatch-api
Frontend Container App: safewatch-ui
API Gateway: Azure API Management
Cosmos DB: safewatch / safewatch / incidents
Log Analytics Workspace: law-safewatch-v1
LangSmith Project: safewatch-ai-v1
```

Deployed API flow:

```text
SafeWatch UI
  -> Azure API Management
  -> safewatch-api Container App
  -> LangGraph agents
  -> Azure AI services / Cosmos DB / Blob Storage
```

API gateway base:

```text
https://apim-safewatch-v1-ashifa.azure-api.net
```

Typical configured API path:

```text
https://apim-safewatch-v1-ashifa.azure-api.net/safewatch
```

## Human Review Flow

```text
Work-start request
  -> Evidence upload / incident metadata
  -> LangGraph workflow
  -> Vision + Document + Compliance RAG
  -> Risk Scoring
  -> Governance Agent
  -> auto_log OR pending_review
  -> Human Review Queue
  -> HSE Manager / Escalation Committee
  -> approve or reject
  -> Cosmos DB audit event
```

Governance examples:

- Low risk and valid permit -> auto-log.
- Missing permit number -> HSE manager review.
- Missing fall protection at height -> high severity review.
- Critical or escalated risk -> escalation committee.

## Audit Model

Blob Storage stores raw evidence files:

```text
permit PDF
site image
future safety attachments
```

Cosmos DB stores structured workflow records:

```text
incident
agent_run
risk_assessment
governance_decision
reviewer_packet
audit_event
```

If no file is uploaded, the incident may have an empty evidence array. The design still keeps the separation:

```text
Blob Storage = raw files
Cosmos DB = metadata, decisions, audit trail, and file references
```

## Monitoring and Tracing

Azure monitoring:

- Azure Monitor
- Log Analytics Workspace
- ContainerAppConsoleLogs_CL
- Azure Workbook: SafeWatch AI Monitoring
- Alerts for API errors and agent failures

LangSmith tracing:

- Project: `safewatch-ai-v1`
- Parent run: `LangGraph`
- Child workflow steps:
  - `create_incident`
  - `vision_agent`
  - `document_agent`
  - `compliance_rag_agent`
  - `risk_scoring_agent`
  - `governance_agent`
  - `report_agent`
  - `persist_outputs`

Tracing is centralized in the orchestration layer:

```text
config.py       -> reads LangSmith environment variables
orchestrator.py -> invokes LangGraph workflow
graph.py        -> defines nodes and wraps agent execution with telemetry.trace(...)
```

The individual agents contain business logic and do not directly depend on LangSmith.

## Failure Modes

Known failure modes and intended handling:

- **Blob Storage not configured:** `/evidence/upload` returns service unavailable.
- **Missing evidence:** workflow can still run with metadata-only requests, but evidence array may be empty.
- **Azure AI Vision unsupported feature or regional limitation:** Vision service falls back to safer feature combinations.
- **Document Intelligence unavailable:** Document Agent can fall back to mock/local signals for demo mode.
- **Azure AI Search or Azure OpenAI unavailable:** Compliance RAG may return fallback citations or reduced retrieval output.
- **High-risk governance decision:** incident is routed to human review instead of closure.
- **Approval/rejection on non-pending incident:** API returns conflict to protect audit integrity.
- **Agent exception:** agent run is marked failed and error details are retained.
- **API errors:** visible through Azure Monitor / Log Analytics queries.
- **Slow agent run:** visible through LangSmith latency and run tree.

## Security Notes

This is a v1 demo implementation.

- Do not commit `.env` files or real secrets.
- Use Azure Container App secrets or Key Vault references for production.
- Prefer Managed Identity for Azure resource access.
- Restrict public access for production deployments.
- Add Entra ID / JWT authentication before production use.
- Add Azure Front Door and WAF for enterprise edge protection.
- Use least-privilege RBAC for Cosmos DB, Storage, AI Search, and Azure OpenAI.
- Rotate demo tokens and API keys after public demos.

## Current Status

**Completed:**

- FastAPI backend.
- Static SafeWatch frontend.
- Backend Dockerfile.
- Frontend Dockerfile.
- Azure Container Apps deployment.
- Azure API Management gateway.
- Blob Storage evidence upload design.
- Azure AI Vision integration.
- Azure Document Intelligence integration.
- Azure AI Search regulation index.
- Azure OpenAI chat and embedding integration.
- LangGraph multi-agent workflow.
- Risk scoring and governance rules.
- Reviewer packet generation.
- Human Review Queue.
- Approve / reject workflow.
- Cosmos DB audit events.
- Azure Monitor and Workbook monitoring.
- LangSmith tracing.
- GitHub repository.
- End-to-end verification tests.

**Pending production hardening:**

- Entra ID / JWT authentication.
- Role-based access control.
- Azure Front Door custom domain and WAF policy.
- Key Vault and Managed Identity hardening.
- Private endpoints and VNet integration.
- Service Bus async agent processing.
- Multi-region load balancing.
- GitHub Actions CI/CD deployment pipeline.
- Expanded production safety datasets.

## When the LLM Is Triggered

LLM/RAG path is used for compliance retrieval and grounded safety reasoning.

Example:

```text
Work at height image shows scaffold and missing harness.
Permit has missing or expired approval details.
```

Flow:

```text
/incidents/analyze
  -> LangGraph
  -> Vision Agent detects safety signals
  -> Document Agent validates permit signals
  -> Compliance RAG Agent retrieves safety citations
  -> Azure OpenAI helps ground regulatory context
  -> Risk Scoring Agent computes risk
  -> Governance Agent decides review route
  -> Report Agent creates reviewer packet
```

## LLM Not Triggered

These operations are deterministic or direct API operations:

```text
/health
/config/status
/evidence/upload
/incidents/{incident_id}/records
/incidents/{incident_id}/review
approve incident
reject incident
basic risk threshold application
Cosmos DB audit event persistence
```

## Useful Documentation

- [API contracts](docs/api-contracts.md)
- [Architecture diagram source](docs/architecture-diagram.mmd)
- [Implementation roadmap](docs/implementation-roadmap.md)
- [Azure console checklist](docs/phase-0-1-azure-console-checklist.md)
- [Detailed architecture](docs/safewatch-ai-v1-architecture.md)
