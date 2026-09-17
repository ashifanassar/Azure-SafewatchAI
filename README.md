# SafeWatch AI

SafeWatch AI is an agentic site safety and compliance platform built on Azure.

The v1 build proves the enterprise governance loop:

```text
Ingestion -> Orchestrator -> Vision / Document / Compliance RAG -> Risk Scoring -> Governance -> Report -> HITL -> Incident + Audit Store
```

## v1 Build Scope

- Static image PPE detection.
- Permit and safety document validation.
- Compliance RAG over OSHAD, TRAKHEES, MOMRA, and ISO 45001.
- Weighted risk scoring.
- Deterministic governance policy rules.
- Human-in-the-loop approval workflow.
- Operations Console.
- Governance Dashboard with model/policy operations as a tab.

## Architecture Principle

The LLM proposes. Deterministic policy disposes. A human approves.

Every consequential action, including escalation, closure, and contractor flagging, passes through governance rules and the required human gate.


## Production Hardening Path

Azure Front Door, WAF, API Management, Service Bus, an audit data lake, Watcher Agent, and predictive safety are designed as the production hardening path, not the v1 build. v1 focuses on proving the end-to-end governance loop with a deployed and testable inner core.

## Local Verification

Run the contract test suite:

```powershell
& 'C:\Users\ashif\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests
```

## Backend Container

Build the FastAPI backend image from the repository root:

```powershell
docker build -f apps/api/Dockerfile -t safewatch-api:local .
```

Run it locally:

```powershell
docker run --rm -p 8000:8000 safewatch-api:local
```

Then open:

```text
http://localhost:8000/health
```

## Frontend Container

The v1 frontend is a lightweight static UI with the two agreed screens:

- Operations Console for submitting safety evidence into the agent workflow.
- Governance Dashboard for reviewing risk, governance routing, citations, and model configuration.

Build the frontend image from the repository root:

```powershell
docker build -f apps/frontend/Dockerfile -t safewatch-ui:local .
```

The deployed UI calls the FastAPI backend `/config/status` and `/incidents/analyze` endpoints.

The backend API invokes the core agent flow through a LangGraph workflow:

```text
create_incident -> vision_agent -> document_agent -> compliance_rag_agent -> risk_scoring_agent -> governance_agent -> report_agent -> persist_outputs
```

## Phase 0 and Phase 1

Use [docs/phase-0-1-azure-console-checklist.md](docs/phase-0-1-azure-console-checklist.md) while creating the first Azure resources through the portal. The matching Bicep baseline is under [infra/bicep](infra/bicep).
