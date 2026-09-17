# SafeWatch AI - Implementation Tasks

## Phase 0: Repository & Foundational Setup

- [x] Initialize repository structure.
- [ ] Configure protected `main` branch.
- [x] Configure CI pipeline for PRs.
- [x] Commit ADR and architecture diagram source.
- [x] Set up implementation task checklist.
- [ ] Set up project milestones and track issues by dependency.

## Phase 1: Infrastructure & Security

- [x] Initialize Bicep project structure.
- [ ] Provision Azure Resource Group using deployment `targetScope`.
- [x] Define Log Analytics Workspace and Application Insights in Bicep.
- [x] Define Azure Container Apps Environment in Bicep.
- [x] Define Azure Cosmos DB Core SQL API in Bicep.
- [x] Define Azure Storage Account for image/document blobs in Bicep.
- [ ] Provision Azure AI Services in UAE North for chat and embeddings.
- [x] Define Azure AI Search for Compliance RAG in Bicep.
- [ ] Configure system-assigned Managed Identities and RBAC roles.
- [x] Add Bicep outputs for required resource names and endpoints.

## Phase 2: Core Agentic Workflow

- [x] Initialize Python contract package.
- [x] Build Pydantic interface contracts.
- [x] Add isolated contract tests.
- [x] Initialize FastAPI backend project.
- [x] Initialize LangGraph orchestrator.
- [x] Configure `DefaultAzureCredential` for Managed Identity authentication.
- [x] Implement retry and timeout handling for model/service calls.
- [x] Integrate Application Insights telemetry abstraction for agent traces.
- [x] Build Vision Agent for PPE and site hazard analysis.
- [x] Build Document Agent for permit extraction and validation.
- [x] Build RAG Agent for regulatory retrieval and citations.
- [x] Build Report Agent for the cited reviewer packet.
- [x] Build Risk Scoring Agent for composite risk scoring.
- [x] Build Governance Agent with hard overrides first, then risk-band routing.
- [x] Implement Cosmos DB repository for incident records and audit trail.

## Phase 3: Frontends

- [ ] Initialize Next.js frontend project.
- [ ] Set up UI component library and styling.
- [ ] Build Operations Console image/document upload interface.
- [ ] Build Operations Console submission trigger.
- [ ] Build real-time status polling or updates.
- [ ] Build Governance Dashboard risk queue for incidents with risk >= 30.
- [ ] Build incident details view with vision annotations and RAG citations.
- [ ] Build approval/rejection workflow.
- [ ] Build Model Ops tab for metrics/traces or a basic trace viewer.

## Phase 4: Deployment & Documentation

- [x] Dockerize Python backend.
- [ ] Dockerize Next.js frontend.
- [ ] Deploy backend to Azure Container Apps.
- [ ] Deploy frontend to Azure Container Apps.
- [ ] Write README deployment instructions.
- [ ] Add failure-modes documentation.
- [ ] Run end-to-end verification test.
