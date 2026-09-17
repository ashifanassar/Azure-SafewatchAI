# ADR-0001: SafeWatch AI v1 Architecture Baseline

## Status

Accepted

## Context

SafeWatch AI v1 needs to prove the end-to-end safety governance loop without overbuilding production hardening services that do not change the demo outcome.

The v1 system processes static site images, permits, safety documents, and site metadata through a governed agent chain. The key interview and engineering value is the controlled decision workflow: AI agents can detect, retrieve, summarize, and recommend, but deterministic policy rules and human review control consequential actions.

## Decision

We will build the v1 inner core:

- Operations Console and Governance Dashboard only.
- FastAPI backend hosted on Azure Container Apps.
- LangGraph orchestrator for the agent workflow.
- Azure Blob Storage for image and document evidence.
- Azure Event Grid for batch evidence workflow triggers.
- Azure Cosmos DB Core SQL API as the single v1 incident and audit store.
- Azure AI Vision or a custom PPE model for image analysis.
- Azure AI Document Intelligence for permit/document extraction.
- Azure AI Search and Azure OpenAI for Compliance RAG.
- Deterministic Risk Scoring and Governance Agents.
- Azure Logic Apps for human approval routing.
- Managed Identity, Key Vault, Application Insights, retry handling, and timeout handling as v1 controls.

Production hardening services are designed but deferred:

- Azure Front Door and WAF.
- Azure API Management.
- Azure Service Bus.
- Audit data lake.
- Watcher Agent.
- Predictive safety layer.
- Multi-tenant production RBAC.

## Governance Routing

Hard overrides evaluate before risk-band routing:

- Expired permit blocks closure.
- Contractor threshold breach escalates.
- Missing harness at height enforces a minimum high-risk band.

Risk-band routing:

- Risk `< 30`: auto-log.
- Risk `30-59`: Safety Officer review.
- Risk `60-79`: HSE Manager review.
- Risk `>= 80`: Escalation Committee review.

Every governance decision records the policy version.

## Consequences

The v1 implementation remains small enough to finish, test, deploy, and explain clearly. The production hardening path remains visible for architecture credibility without consuming v1 build time.

