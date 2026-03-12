param name string
param location string = resourceGroup().location
param tags object = {}

param identityName string
param containerAppsEnvironmentName string
param containerRegistryName string
param serviceName string = 'aca'
param exists bool
param appRole string = 'api'
param ingressEnabled bool = true
param external bool = true
param containerMinReplicas int = 1
param containerMaxReplicas int = 10
param targetPort int = 50505

// Environment variables for the backend
param storageAccountName string = ''
param storageContainerName string = 'tender-documents'
param uipathTenantName string = ''
param uipathAppId string = ''
param uipathApiKey string = ''
param uipathFolderId string = ''
param uipathQueueName string = ''
param uipathMockMode string = 'false'

// Frontend configuration parameters
param entraClientId string = ''
param entraTenantId string = ''
param sharePointBaseUrl string = ''

// M-Files configuration parameters
param mfilesBaseUrl string = ''
param mfilesClientId string = ''
@secure()
param mfilesClientSecret string = ''
param mfilesDefaultsAdminGroupIds string = ''

// Data Fabric configuration parameters
param dataFabricApiUrl string = ''
param dataFabricApiKey string = ''
param webhookBatchCompleteKey string = ''

// Batch progress polling configuration
param batchProgressPollingInterval string = '30000'

// Cosmos metadata configuration
param cosmosAccountEndpoint string = ''
param cosmosDatabaseName string = 'kapitol-tender-automation'
param cosmosMetadataContainerName string = 'metadata'
param cosmosBatchReferenceContainerName string = 'batch-reference-index'
param metadataStoreMode string = 'blob'
param metadataReadFallback string = 'true'
param azureOpenAiEndpoint string = ''
param azureOpenAiExtractionDeployment string = ''
@secure()
param azureOpenAiApiKey string = ''
param extractionQueueName string = 'drawing-extraction'
param extractionRenderDpi string = '300'
param extractionWorkerConcurrency string = '2'
@secure()
param applicationInsightsConnectionString string = ''
param queueScaleEnabled bool = false
param queueScaleRuleName string = 'drawing-extraction'
param queueScaleQueueName string = 'drawing-extraction'
param queueScaleQueueLength string = '1'
param queueScaleAccountName string = ''
@secure()
param queueScaleConnectionString string = ''

@description('Custom domain hostname (optional)')
param customHostName string = ''

@description('Custom domain certificate name (optional)')
param customCertificateName string = ''

resource acaIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

// Build environment variables array conditionally
var baseEnvVars = [
  {
    name: 'AZURE_CLIENT_ID'
    value: acaIdentity.properties.clientId
  }
  {
    name: 'APP_ROLE'
    value: appRole
  }
  {
    name: 'AZURE_STORAGE_ACCOUNT_NAME'
    value: storageAccountName
  }
  {
    name: 'AZURE_STORAGE_CONTAINER_NAME'
    value: storageContainerName
  }
  {
    name: 'UIPATH_TENANT_NAME'
    value: uipathTenantName
  }
  {
    name: 'UIPATH_APP_ID'
    value: uipathAppId
  }
  {
    name: 'UIPATH_FOLDER_ID'
    value: uipathFolderId
  }
  {
    name: 'UIPATH_QUEUE_NAME'
    value: uipathQueueName
  }
  {
    name: 'UIPATH_MOCK_MODE'
    value: uipathMockMode
  }
  {
    name: 'ENTRA_CLIENT_ID'
    value: entraClientId
  }
  {
    name: 'ENTRA_TENANT_ID'
    value: entraTenantId
  }
  {
    name: 'SHAREPOINT_BASE_URL'
    value: sharePointBaseUrl
  }
  {
    name: 'MFILES_BASE_URL'
    value: mfilesBaseUrl
  }
  {
    name: 'MFILES_CLIENT_ID'
    value: mfilesClientId
  }
  {
    name: 'MFILES_DEFAULTS_ADMIN_GROUP_IDS'
    value: mfilesDefaultsAdminGroupIds
  }
  {
    name: 'DATA_FABRIC_API_URL'
    value: dataFabricApiUrl
  }
  {
    name: 'BATCH_PROGRESS_POLLING_INTERVAL'
    value: batchProgressPollingInterval
  }
  {
    name: 'COSMOS_ACCOUNT_ENDPOINT'
    value: cosmosAccountEndpoint
  }
  {
    name: 'COSMOS_DATABASE_NAME'
    value: cosmosDatabaseName
  }
  {
    name: 'COSMOS_METADATA_CONTAINER_NAME'
    value: cosmosMetadataContainerName
  }
  {
    name: 'COSMOS_BATCH_REFERENCE_CONTAINER_NAME'
    value: cosmosBatchReferenceContainerName
  }
  {
    name: 'METADATA_STORE_MODE'
    value: metadataStoreMode
  }
  {
    name: 'METADATA_READ_FALLBACK'
    value: metadataReadFallback
  }
  {
    name: 'AZURE_OPENAI_ENDPOINT'
    value: azureOpenAiEndpoint
  }
  {
    name: 'AZURE_OPENAI_EXTRACTION_DEPLOYMENT'
    value: azureOpenAiExtractionDeployment
  }
  {
    name: 'EXTRACTION_QUEUE_NAME'
    value: extractionQueueName
  }
  {
    name: 'EXTRACTION_RENDER_DPI'
    value: extractionRenderDpi
  }
  {
    name: 'EXTRACTION_WORKER_CONCURRENCY'
    value: extractionWorkerConcurrency
  }
]

var uipathApiKeyEnvVar = !empty(uipathApiKey)
  ? [
      {
        name: 'UIPATH_API_KEY'
        secretRef: 'uipath-api-key'
      }
    ]
  : []

var dataFabricApiKeyEnvVar = !empty(dataFabricApiKey)
  ? [
      {
        name: 'DATA_FABRIC_API_KEY'
        secretRef: 'data-fabric-api-key'
      }
    ]
  : []

var mfilesClientSecretEnvVar = !empty(mfilesClientSecret)
  ? [
      {
        name: 'MFILES_CLIENT_SECRET'
        secretRef: 'mfiles-client-secret'
      }
    ]
  : []

var webhookBatchCompleteKeyEnvVar = !empty(webhookBatchCompleteKey)
  ? [
      {
        name: 'WEBHOOK_BATCH_COMPLETE_KEY'
        secretRef: 'webhook-batch-complete-key'
      }
    ]
  : []

var applicationInsightsConnectionStringEnvVar = !empty(applicationInsightsConnectionString)
  ? [
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        secretRef: 'applicationinsights-connection-string'
      }
    ]
  : []

var azureOpenAiApiKeyEnvVar = !empty(azureOpenAiApiKey)
  ? [
      {
        name: 'AZURE_OPENAI_API_KEY'
        secretRef: 'azure-openai-api-key'
      }
    ]
  : []

var allEnvVars = concat(
  baseEnvVars,
  uipathApiKeyEnvVar,
  dataFabricApiKeyEnvVar,
  mfilesClientSecretEnvVar,
  webhookBatchCompleteKeyEnvVar,
  applicationInsightsConnectionStringEnvVar,
  azureOpenAiApiKeyEnvVar
)

// Build secrets array conditionally
var baseSecrets = [
  {
    name: 'override-use-mi-fic-assertion-client-id'
    value: acaIdentity.properties.clientId
  }
]

var uipathApiKeySecret = !empty(uipathApiKey)
  ? [
      {
        name: 'uipath-api-key'
        value: uipathApiKey
      }
    ]
  : []

var dataFabricApiKeySecret = !empty(dataFabricApiKey)
  ? [
      {
        name: 'data-fabric-api-key'
        value: dataFabricApiKey
      }
    ]
  : []

var mfilesClientSecretSecret = !empty(mfilesClientSecret)
  ? [
      {
        name: 'mfiles-client-secret'
        value: mfilesClientSecret
      }
    ]
  : []

var webhookBatchCompleteKeySecret = !empty(webhookBatchCompleteKey)
  ? [
      {
        name: 'webhook-batch-complete-key'
        value: webhookBatchCompleteKey
      }
    ]
  : []

var applicationInsightsConnectionStringSecret = !empty(applicationInsightsConnectionString)
  ? [
      {
        name: 'applicationinsights-connection-string'
        value: applicationInsightsConnectionString
      }
    ]
  : []

var azureOpenAiApiKeySecret = !empty(azureOpenAiApiKey)
  ? [
      {
        name: 'azure-openai-api-key'
        value: azureOpenAiApiKey
      }
    ]
  : []

var queueScaleConnectionStringSecret = queueScaleEnabled && !empty(queueScaleConnectionString)
  ? [
      {
        name: 'queue-scale-connection-string'
        value: queueScaleConnectionString
      }
    ]
  : []

var allSecrets = concat(
  baseSecrets,
  uipathApiKeySecret,
  dataFabricApiKeySecret,
  mfilesClientSecretSecret,
  webhookBatchCompleteKeySecret,
  applicationInsightsConnectionStringSecret,
  azureOpenAiApiKeySecret,
  queueScaleConnectionStringSecret
)

var scaleRules = queueScaleEnabled
  ? [
      {
        name: queueScaleRuleName
        custom: {
          type: 'azure-queue'
          auth: [
            {
              secretRef: 'queue-scale-connection-string'
              triggerParameter: 'connection'
            }
          ]
          metadata: {
            accountName: queueScaleAccountName
            queueLength: queueScaleQueueLength
            queueName: queueScaleQueueName
          }
        }
      }
    ]
  : []

module app 'core/host/container-app-upsert.bicep' = {
  name: '${serviceName}-container-app-module'
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    identityName: acaIdentity.name
    exists: exists
    containerAppsEnvironmentName: containerAppsEnvironmentName
    containerRegistryName: containerRegistryName
    containerMinReplicas: containerMinReplicas
    containerMaxReplicas: containerMaxReplicas
    env: allEnvVars
    scaleRules: scaleRules
    external: external
    ingressEnabled: ingressEnabled
    targetPort: targetPort
    secrets: allSecrets
    customHostName: customHostName
    customCertificateName: customCertificateName
  }
}

output identityPrincipalId string = acaIdentity.properties.principalId
output name string = app.outputs.name
output uri string = app.outputs.uri
output imageName string = app.outputs.imageName
output identityResourceId string = app.outputs.identityResourceId
