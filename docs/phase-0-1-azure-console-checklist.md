# SafeWatch AI Phase 0 and Phase 1 Console Checklist

## Phase 0: Repository and Planning

Use the repo to complete these items before deploying cloud resources.

- Confirm `README.md` explains the architecture.
- Confirm `TASKS.md` tracks Phase 0 through Phase 4.
- Confirm ADR exists: `docs/adr/0001-v1-architecture-baseline.md`.
- Confirm architecture source exists: `docs/architecture-diagram.mmd`.
- Confirm contract package exists under `packages/contracts`.
- Run contract tests:

```powershell
& 'C:\Users\ashif\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests
```

Items that require GitHub after pushing:

- Protect `main`.
- Require PR checks.
- Create v1 milestone.
- Create issues sequenced by dependency.

## Phase 1: Azure Infrastructure and Security

Create resources in this order from the Azure Portal.

### 1. Resource Group

Name:

```text
rg-safewatch-v1-uaenorth
```

Region:

```text
UAE North
```

### 2. Log Analytics and Application Insights

Create:

- Log Analytics Workspace.
- Application Insights connected to the workspace.

Purpose:

- Agent traces.
- Workflow telemetry.
- Model call latency.
- Retry and timeout visibility.

### 3. Storage Account

Create a StorageV2 account with Standard LRS.

Recommended containers:

- `evidence-images`
- `evidence-documents`
- `generated-reports`

Security:

- Disable public blob access.
- Require HTTPS.
- Use TLS 1.2 or later.

### 4. Cosmos DB for NoSQL

Create Azure Cosmos DB for NoSQL.

Database:

```text
safewatch
```

Containers:

| Container | Partition Key |
| --- | --- |
| `incidents` | `/incident_id` |
| `agent_runs` | `/incident_id` |
| `audit_events` | `/incident_id` |
| `policies` | `/policy_version` |

Use serverless for v1 if available.

### 5. Azure AI Search

Create an Azure AI Search service.

Purpose:

- Compliance RAG index for OSHAD, TRAKHEES, MOMRA, and ISO 45001.

Use Basic unless Free is available and enough for your subscription.

### 6. Azure AI Services / Azure OpenAI

Create the available AI resources in UAE North where supported.

Needed capabilities:

- Chat model for RAG explanation and Report Agent.
- Embedding model for regulatory corpus indexing.
- Document Intelligence for permit extraction.
- Vision or custom PPE endpoint for image analysis.

Important:

- Verify model availability in your subscription and region before documenting final model names.
- If chat model deployment uses GlobalStandard routing, document it honestly.

### 7. Key Vault

Create Key Vault with RBAC authorization enabled.

Purpose:

- Store unavoidable secrets and environment configuration.
- Prefer Managed Identity over storing keys.

### 8. Container Apps Environment

Create Azure Container Apps Environment connected to Log Analytics.

Later container apps:

- `safewatch-api`
- `safewatch-operations-console`
- `safewatch-governance-dashboard`

### 9. Managed Identity and RBAC

After creating the backend Container App, enable system-assigned Managed Identity.

Assign least-privilege roles:

- Storage Blob Data Contributor on Storage Account.
- Cosmos DB data contributor role on Cosmos DB.
- Search Index Data Contributor on Azure AI Search.
- Cognitive Services User on AI resources.
- Key Vault Secrets User on Key Vault.

### 10. Event Grid

Create Event Grid subscription after backend endpoint exists.

Trigger:

- Blob created in `evidence-images` or `evidence-documents`.

Target:

- Backend ingestion endpoint or orchestrator endpoint.

## Phase 1 Done Criteria

Phase 1 is done when:

- The resource group exists.
- Storage containers exist.
- Cosmos DB database and containers exist.
- Log Analytics and Application Insights exist.
- Azure AI Search exists.
- Required AI resources are created or blocked with documented reason.
- Key Vault exists.
- Container Apps Environment exists.
- Managed Identity/RBAC plan is documented.
- Bicep baseline exists under `infra/bicep`.

