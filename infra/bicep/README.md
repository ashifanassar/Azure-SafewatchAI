# SafeWatch AI v1 Infrastructure

This folder contains the Phase 1 Azure Bicep baseline for SafeWatch AI.

## Resources

- Log Analytics Workspace.
- Application Insights.
- Azure Storage Account.
- Blob containers:
  - `evidence-images`
  - `evidence-documents`
  - `generated-reports`
- Azure Cosmos DB for NoSQL.
- Cosmos DB database:
  - `safewatch`
- Cosmos DB containers:
  - `incidents` partitioned by `/incident_id`
  - `agent_runs` partitioned by `/incident_id`
  - `audit_events` partitioned by `/incident_id`
  - `policies` partitioned by `/policy_version`
- Azure AI Search.
- Azure Key Vault with RBAC authorization.
- Azure Container Apps Environment.

## Portal-First Phase 1

If you are learning through the Azure Portal first, create the same resources manually using the names and settings in `main.bicep`. After that, use Bicep to reproduce the environment.

## Deploy Later With Azure CLI

```powershell
az group create --name rg-safewatch-v1-uaenorth --location uaenorth

az deployment group create `
  --resource-group rg-safewatch-v1-uaenorth `
  --template-file infra/bicep/main.bicep `
  --parameters infra/bicep/main.parameters.json
```

## Notes

- Cosmos DB is serverless in v1 to keep cost and operations small.
- Service Bus, API Management, Front Door, WAF, Watcher Agent, and predictive safety are intentionally deferred.
- Azure AI model deployments are not created in this Bicep baseline yet because model availability and deployment SKUs must be verified in the target subscription and region.

