targetScope = 'resourceGroup'

@description('Azure region for SafeWatch AI v1 resources.')
param location string = resourceGroup().location

@description('Short environment name used in resource names.')
@allowed([
  'dev'
  'test'
  'prod'
])
param environmentName string = 'dev'

@description('Project name used for tagging and resource naming.')
param projectName string = 'safewatch'

@description('Azure AI Search SKU for v1. Use free where allowed, otherwise basic.')
@allowed([
  'free'
  'basic'
  'standard'
])
param searchSku string = 'basic'

@description('Enable Cosmos DB free tier if the subscription has not already used it.')
param enableCosmosFreeTier bool = false

var normalizedProject = toLower(replace(projectName, '-', ''))
var suffix = toLower(uniqueString(resourceGroup().id))
var resourcePrefix = '${normalizedProject}-${environmentName}'
var storageName = take('${normalizedProject}${environmentName}${suffix}', 24)
var cosmosName = '${resourcePrefix}-cosmos-${suffix}'
var searchName = '${resourcePrefix}-search-${suffix}'
var workspaceName = '${resourcePrefix}-law-${suffix}'
var appInsightsName = '${resourcePrefix}-appi-${suffix}'
var containerEnvName = '${resourcePrefix}-acaenv-${suffix}'
var keyVaultName = take('${normalizedProject}-${environmentName}-kv-${suffix}', 24)
var tags = {
  project: 'SafeWatch AI'
  environment: environmentName
  phase: 'v1'
  managedBy: 'bicep'
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource evidenceImages 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'evidence-images'
  properties: {
    publicAccess: 'None'
  }
}

resource evidenceDocuments 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'evidence-documents'
  properties: {
    publicAccess: 'None'
  }
}

resource generatedReports 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'generated-reports'
  properties: {
    publicAccess: 'None'
  }
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: cosmosName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    enableFreeTier: enableCosmosFreeTier
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
}

resource safewatchDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'safewatch'
  properties: {
    resource: {
      id: 'safewatch'
    }
  }
}

resource incidentsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: safewatchDb
  name: 'incidents'
  properties: {
    resource: {
      id: 'incidents'
      partitionKey: {
        paths: [
          '/incident_id'
        ]
        kind: 'Hash'
      }
    }
  }
}

resource agentRunsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: safewatchDb
  name: 'agent_runs'
  properties: {
    resource: {
      id: 'agent_runs'
      partitionKey: {
        paths: [
          '/incident_id'
        ]
        kind: 'Hash'
      }
    }
  }
}

resource auditEventsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: safewatchDb
  name: 'audit_events'
  properties: {
    resource: {
      id: 'audit_events'
      partitionKey: {
        paths: [
          '/incident_id'
        ]
        kind: 'Hash'
      }
    }
  }
}

resource policiesContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: safewatchDb
  name: 'policies'
  properties: {
    resource: {
      id: 'policies'
      partitionKey: {
        paths: [
          '/policy_version'
        ]
        kind: 'Hash'
      }
    }
  }
}

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchName
  location: location
  tags: tags
  sku: {
    name: searchSku
  }
  properties: {
    hostingMode: 'default'
    partitionCount: 1
    replicaCount: 1
    publicNetworkAccess: 'enabled'
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    sku: {
      family: 'A'
      name: 'standard'
    }
  }
}

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerEnvName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

output location string = location
output storageAccountName string = storage.name
output evidenceImagesContainer string = evidenceImages.name
output evidenceDocumentsContainer string = evidenceDocuments.name
output generatedReportsContainer string = generatedReports.name
output cosmosAccountName string = cosmos.name
output cosmosDatabaseName string = safewatchDb.name
output searchServiceName string = search.name
output logAnalyticsWorkspaceName string = logAnalytics.name
output applicationInsightsName string = appInsights.name
output applicationInsightsConnectionString string = appInsights.properties.ConnectionString
output containerAppsEnvironmentName string = containerAppsEnv.name
output keyVaultName string = keyVault.name

