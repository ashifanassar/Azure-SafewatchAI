# SafeWatch AI v1 - Architecture Documentation

**Platform:** Microsoft Azure  
**Version:** v1 demo-ready implementation  
**Architecture file:** `SafeWatch_AI_v1_Architecture.drawio`

---

## Architecture Summary

SafeWatch AI v1 is an agentic HSE governance platform for work-start safety review. It accepts site evidence, analyzes work permits and site images, retrieves compliance citations, scores risk, applies deterministic governance rules, and routes high-risk cases to human review.

The architecture follows this flow:

```text
SafeWatch Web UI
  -> Azure Front Door + WAF
  -> Azure API Management
  -> Azure Container Apps backend
  -> LangGraph multi-agent workflow
  -> Azure AI services and data stores
  -> Governance Dashboard / Human Review Queue
  -> Cosmos DB audit trail
```

---

## Layered Architecture

| Layer | Component | Purpose |
|---|---|---|
| 1 | User Interface | SafeWatch browser UI for operations and governance review |
| 2 | Edge Security | Azure Front Door and WAF for enterprise edge protection |
| 3 | API Gateway | Azure API Management for routing API traffic to the backend |
| 4 | Application Runtime | Azure Container Apps hosting the frontend and FastAPI backend |
| 5 | Agent Orchestration | LangGraph workflow coordinating the safety agents |
| 6 | AI Services | Azure AI Vision, Document Intelligence, Azure OpenAI, Azure AI Search |
| 7 | Data Layer | Blob Storage for evidence files and Cosmos DB for workflow records |
| 8 | Human Review | HSE Manager / Escalation Committee approve-reject workflow |
| 9 | Observability | Azure Monitor, Log Analytics, Azure Workbook, and LangSmith tracing |

---

## Agent Workflow

```text
create_incident
  -> vision_agent
  -> document_agent
  -> compliance_rag_agent
  -> risk_scoring_agent
  -> governance_agent
  -> report_agent
  -> persist_outputs
```

| Agent | Responsibility |
|---|---|
| Vision Agent | Analyzes site images for PPE, harness, helmet, scaffold, ladder, roof, elevated platform, and fall hazards |
| Document Agent | Validates permit number, work type, permit status, expiry, and approval information |
| Compliance RAG Agent | Retrieves ISO 45001 / OSHAD / HSE regulation citations |
| Risk Scoring Agent | Computes risk score and risk band |
| Governance Agent | Applies deterministic policy rules and decides auto-log or human review |
| Report Agent | Builds the reviewer packet with findings, citations, and recommended action |
| Persist Outputs | Stores incident records, reviewer packet, risk, governance decision, and audit events |

---

## Data Storage Pattern

| Store | What It Contains |
|---|---|
| Azure Blob Storage | Raw evidence files such as permit PDFs, site images, and future attachments |
| Azure Cosmos DB | Incident records, risk assessments, governance decisions, reviewer packets, agent runs, and audit events |

Simple rule:

```text
Blob Storage = raw files
Cosmos DB = metadata, decisions, reviewer packet, and audit trail
```

---

## Governance Flow

```text
Work-start request
  -> Evidence / incident metadata
  -> Multi-agent analysis
  -> Risk score
  -> Governance decision
  -> Auto-log OR pending human review
  -> Approve / Reject
  -> Audit event stored in Cosmos DB
```

Governance examples:

- Low risk with valid permit: auto-log.
- Missing permit number: HSE manager review.
- Missing fall protection at height: high-risk review.
- Critical risk: escalation committee review.

---

## Observability

SafeWatch AI v1 includes two monitoring layers:

| Tool | Purpose |
|---|---|
| Azure Monitor + Log Analytics | API logs, container logs, error queries, operational monitoring |
| Azure Workbook | Visual dashboard for agent runs, traces, and errors |
| LangSmith | LangGraph run tree, agent latency, inputs, outputs, and debugging |

LangSmith tracing is centralized in the orchestration layer:

```text
config.py       -> reads LangSmith environment variables
orchestrator.py -> invokes the LangGraph workflow
graph.py        -> defines graph nodes and wraps agent execution with telemetry tracing
```

Individual agent files contain business logic and do not directly depend on LangSmith.

---

## Implemented v1 Scope

- SafeWatch Web UI
- FastAPI backend
- Azure Container Apps deployment
- Azure API Management gateway
- LangGraph multi-agent orchestration
- Azure AI Vision integration
- Azure Document Intelligence integration
- Azure OpenAI integration
- Azure AI Search regulation retrieval
- Cosmos DB persistence and audit events
- Blob Storage evidence design
- Human review approve/reject flow
- Governance Dashboard
- Azure Monitor / Log Analytics monitoring
- LangSmith tracing

---

## Future Production Hardening

- Entra ID / JWT authentication
- Role-based access control
- Azure Front Door custom domain and WAF policy
- Azure Key Vault and Managed Identity hardening
- Private endpoints and VNet integration
- Azure Service Bus async agent processing
- Multi-region load balancing
- GitHub Actions CI/CD deployment pipeline
- Expanded production safety datasets

---

## Files

| File | Description |
|---|---|
| `ARCHITECTURE.md` | This architecture summary |
| `SafeWatch_AI_v1_Architecture.drawio` | Editable diagrams.net / draw.io source file |
| `SafeWatch_AI_v1_Architecture.png` | Optional exported PNG for GitHub preview |
