targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name which is used to generate a short unique hash for each resource')
param name string

@minLength(1)
@description('Primary location for all resources')
param location string

param acaExists bool = false
param workerExists bool = false

@description('Custom domain hostname (optional)')
param customHostName string = ''

@description('Custom domain certificate name (optional)')
param customCertificateName string = ''

// A token store is only needed if the app needs to access the Entra access tokens
// https://learn.microsoft.com/azure/container-apps/token-store
param includeTokenStore bool = true

param tokenStorageContainerName string = 'tokens'

@description('Service Management Reference for the app registration')
param serviceManagementReference string = ''

@description('SharePoint base URL for the frontend')
param sharePointBaseUrl string = ''

@description('M-Files API base URL')
param mfilesBaseUrl string = ''

@description('M-Files API client ID')
param mfilesClientId string = ''

@secure()
@description('M-Files API client secret')
param mfilesClientSecret string = ''

@description('Comma-separated Entra group object IDs allowed to manage M-Files queue defaults')
param mfilesDefaultsAdminGroupIds string = ''

@description('Data Fabric API URL')
param dataFabricApiUrl string = ''

@secure()
@description('Data Fabric API Key')
param dataFabricApiKey string = ''

@secure()
@description('Shared secret key required by /api/webhooks/batch-complete header validation')
param webhookBatchCompleteKey string = ''

@description('Azure OpenAI endpoint for internal title-block extraction')
param azureOpenAiEndpoint string = ''

@description('Azure OpenAI deployment name for internal title-block extraction')
param azureOpenAiExtractionDeployment string = ''

@secure()
@description('Azure OpenAI API key for internal title-block extraction')
param azureOpenAiApiKey string = ''

@description('Azure Storage Queue name for internal title-block extraction work')
param extractionQueueName string = 'drawing-extraction'

@description('PDF render DPI for internal title-block extraction')
param extractionRenderDpi string = '300'

@description('Per-replica extraction worker concurrency')
param extractionWorkerConcurrency string = '2'

@description('Batch progress polling interval in milliseconds (default: 30000 = 30 seconds)')
param batchProgressPollingInterval string = '30000'

@description('UiPath Tenant Name')
param uipathTenantName string = ''

@description('UiPath App ID (OAuth Client ID)')
param uipathAppId string = ''

@secure()
@description('UiPath API Key (OAuth Client Secret)')
param uipathApiKey string = ''

@description('UiPath Folder ID (Organization Unit ID)')
param uipathFolderId string = ''

@description('UiPath Queue Name')
param uipathQueueName string = ''

@description('Cosmos SQL database name for metadata')
param cosmosDatabaseName string = 'kapitol-tender-automation'

@description('Cosmos metadata container name')
param cosmosMetadataContainerName string = 'metadata'

@description('Cosmos batch reference index container name')
param cosmosBatchReferenceContainerName string = 'batch-reference-index'

@allowed([
  'blob'
  'dual'
  'cosmos'
])
@description('Metadata store mode for backend')
param metadataStoreMode string = 'blob'

@description('Whether metadata reads can fallback to blob in dual mode')
param metadataReadFallback string = 'true'

var resourceToken = toLower(uniqueString(subscription().id, name, location))
var tags = { 'azd-env-name': name }

resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'RG-${name}'
  location: location
  tags: tags
}

var prefix = toLower('${name}-${resourceToken}')
var storageAccountName = '${take(replace(prefix, '-', ''), 17)}storage'

// Container apps environment (including container registry)
module containerApps 'core/host/container-apps.bicep' = {
  name: 'container-apps'
  scope: resourceGroup
  params: {
    name: 'app'
    location: location
    tags: tags
    containerAppsEnvironmentName: '${prefix}-containerapps-env'
    containerRegistryName: '${replace(prefix, '-', '')}registry'
    logAnalyticsWorkspaceName: logAnalyticsWorkspace.outputs.name
  }
}

module logAnalyticsWorkspace 'core/monitor/loganalytics.bicep' = {
  name: 'loganalytics'
  scope: resourceGroup
  params: {
    name: '${prefix}-loganalytics'
    location: location
    tags: tags
  }
}

module applicationInsights 'core/monitor/applicationinsights.bicep' = {
  name: 'applicationinsights'
  scope: resourceGroup
  params: {
    name: replace('${take(prefix, 35)}-appi', '--', '-')
    dashboardName: replace('${take(prefix, 40)}-appi-dashboard', '--', '-')
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalyticsWorkspace.outputs.id
  }
}

// Storage account for tender documents (created first without role assignments)
module storage 'core/storage/storage-account.bicep' = {
  name: 'storage'
  scope: resourceGroup
  params: {
    name: storageAccountName
    location: location
    tags: tags
    isHnsEnabled: true
    queueName: extractionQueueName
  }
}
var storageAccountKey = listKeys(resourceId(subscription().subscriptionId, resourceGroup.name, 'Microsoft.Storage/storageAccounts', storageAccountName), '2023-01-01').keys[0].value
var storageQueueConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};AccountKey=${storageAccountKey};EndpointSuffix=${environment().suffixes.storage}'

module cosmos 'core/data/cosmos-account.bicep' = {
  name: 'cosmos'
  scope: resourceGroup
  params: {
    name: '${take(replace(prefix, '-', ''), 35)}cosmos'
    location: location
    tags: tags
    databaseName: cosmosDatabaseName
    metadataContainerName: cosmosMetadataContainerName
    batchReferenceContainerName: cosmosBatchReferenceContainerName
  }
}

module aca 'aca.bicep' = {
  name: 'aca'
  scope: resourceGroup
  params: {
    name: replace('${take(prefix,19)}-ca', '--', '-')
    location: location
    tags: tags
    identityName: '${prefix}-id-aca'
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    containerRegistryName: containerApps.outputs.registryName
    exists: acaExists
    appRole: 'api'
    ingressEnabled: true
    external: true
    containerMinReplicas: 1
    containerMaxReplicas: 10
    targetPort: 50505
    storageAccountName: storage.outputs.name
    storageContainerName: storage.outputs.containerName
    uipathMockMode: 'true'
    uipathTenantName: uipathTenantName
    uipathAppId: uipathAppId
    uipathApiKey: uipathApiKey
    uipathFolderId: uipathFolderId
    uipathQueueName: uipathQueueName
    // Frontend configuration - passed after app registration is created
    entraClientId: '' // Will be updated via appupdate
    entraTenantId: tenant().tenantId
    sharePointBaseUrl: sharePointBaseUrl
    mfilesBaseUrl: mfilesBaseUrl
    mfilesClientId: mfilesClientId
    mfilesClientSecret: mfilesClientSecret
    mfilesDefaultsAdminGroupIds: mfilesDefaultsAdminGroupIds
    customHostName: customHostName
    customCertificateName: customCertificateName
    // Data Fabric configuration
    dataFabricApiUrl: dataFabricApiUrl
    dataFabricApiKey: dataFabricApiKey
    webhookBatchCompleteKey: webhookBatchCompleteKey
    // Batch progress polling configuration
    batchProgressPollingInterval: batchProgressPollingInterval
    // Cosmos metadata configuration
    cosmosAccountEndpoint: cosmos.outputs.endpoint
    cosmosDatabaseName: cosmos.outputs.databaseName
    cosmosMetadataContainerName: cosmos.outputs.metadataContainerName
    cosmosBatchReferenceContainerName: cosmos.outputs.batchReferenceContainerName
    metadataStoreMode: metadataStoreMode
    metadataReadFallback: metadataReadFallback
    azureOpenAiEndpoint: azureOpenAiEndpoint
    azureOpenAiExtractionDeployment: azureOpenAiExtractionDeployment
    azureOpenAiApiKey: azureOpenAiApiKey
    extractionQueueName: storage.outputs.queueName
    extractionRenderDpi: extractionRenderDpi
    extractionWorkerConcurrency: extractionWorkerConcurrency
    applicationInsightsConnectionString: applicationInsights.outputs.connectionString
  }
}

module worker 'aca.bicep' = {
  name: 'worker'
  scope: resourceGroup
  params: {
    name: replace('${take(prefix, 19)}-worker', '--', '-')
    location: location
    tags: tags
    identityName: '${prefix}-id-worker'
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    containerRegistryName: containerApps.outputs.registryName
    serviceName: 'worker'
    exists: workerExists
    appRole: 'worker'
    ingressEnabled: false
    external: false
    containerMinReplicas: 0
    containerMaxReplicas: 2
    targetPort: 50505
    storageAccountName: storage.outputs.name
    storageContainerName: storage.outputs.containerName
    uipathMockMode: 'true'
    uipathTenantName: uipathTenantName
    uipathAppId: uipathAppId
    uipathApiKey: uipathApiKey
    uipathFolderId: uipathFolderId
    uipathQueueName: uipathQueueName
    entraClientId: ''
    entraTenantId: tenant().tenantId
    sharePointBaseUrl: sharePointBaseUrl
    mfilesBaseUrl: mfilesBaseUrl
    mfilesClientId: mfilesClientId
    mfilesClientSecret: mfilesClientSecret
    mfilesDefaultsAdminGroupIds: mfilesDefaultsAdminGroupIds
    dataFabricApiUrl: dataFabricApiUrl
    dataFabricApiKey: dataFabricApiKey
    webhookBatchCompleteKey: webhookBatchCompleteKey
    batchProgressPollingInterval: batchProgressPollingInterval
    cosmosAccountEndpoint: cosmos.outputs.endpoint
    cosmosDatabaseName: cosmos.outputs.databaseName
    cosmosMetadataContainerName: cosmos.outputs.metadataContainerName
    cosmosBatchReferenceContainerName: cosmos.outputs.batchReferenceContainerName
    metadataStoreMode: metadataStoreMode
    metadataReadFallback: metadataReadFallback
    azureOpenAiEndpoint: azureOpenAiEndpoint
    azureOpenAiExtractionDeployment: azureOpenAiExtractionDeployment
    azureOpenAiApiKey: azureOpenAiApiKey
    extractionQueueName: storage.outputs.queueName
    extractionRenderDpi: extractionRenderDpi
    extractionWorkerConcurrency: extractionWorkerConcurrency
    applicationInsightsConnectionString: applicationInsights.outputs.connectionString
    queueScaleEnabled: true
    queueScaleRuleName: extractionQueueName
    queueScaleQueueName: storage.outputs.queueName
    queueScaleQueueLength: '1'
    queueScaleAccountName: storage.outputs.name
    queueScaleConnectionString: storageQueueConnectionString
  }
}

// Grant Storage Blob Data Contributor role to the ACA managed identity
// This is done as a separate module to avoid circular dependencies
module storageRoleAssignment 'core/storage/storage-role-assignment.bicep' = {
  name: 'storage-role-assignment'
  scope: resourceGroup
  params: {
    storageAccountName: storage.outputs.name
    principalId: aca.outputs.identityPrincipalId
  }
}

module workerStorageRoleAssignment 'core/storage/storage-role-assignment.bicep' = {
  name: 'worker-storage-role-assignment'
  scope: resourceGroup
  params: {
    storageAccountName: storage.outputs.name
    principalId: worker.outputs.identityPrincipalId
  }
}

module cosmosRoleAssignment 'core/data/cosmos-role-assignment.bicep' = {
  name: 'cosmos-role-assignment'
  scope: resourceGroup
  params: {
    cosmosAccountName: cosmos.outputs.name
    principalId: aca.outputs.identityPrincipalId
  }
}

module workerCosmosRoleAssignment 'core/data/cosmos-role-assignment.bicep' = {
  name: 'worker-cosmos-role-assignment'
  scope: resourceGroup
  params: {
    cosmosAccountName: cosmos.outputs.name
    principalId: worker.outputs.identityPrincipalId
  }
}

var issuer = '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'
module registration 'appregistration.bicep' = {
  name: 'reg'
  scope: resourceGroup
  params: {
    clientAppName: '${prefix}-entra-client-app'
    clientAppDisplayName: 'Tender Automation Client App'
    webAppEndpoint: aca.outputs.uri
    webAppIdentityId: aca.outputs.identityPrincipalId
    issuer: issuer
    serviceManagementReference: serviceManagementReference
    customHostName: customHostName
  }
}

module appupdate 'appupdate.bicep' = {
  name: 'appupdate'
  scope: resourceGroup
  params: {
    containerAppName: aca.outputs.name
    clientId: registration.outputs.clientAppId
    openIdIssuer: issuer
    includeTokenStore: includeTokenStore
    blobContainerUri: includeTokenStore
      ? 'https://${storage.outputs.name}.blob.${environment().suffixes.storage}/${tokenStorageContainerName}'
      : ''
    appIdentityResourceId: includeTokenStore ? aca.outputs.identityResourceId : ''
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId

output SERVICE_ACA_IDENTITY_PRINCIPAL_ID string = aca.outputs.identityPrincipalId
output SERVICE_ACA_NAME string = aca.outputs.name
output SERVICE_ACA_URI string = aca.outputs.uri
output SERVICE_ACA_IMAGE_NAME string = aca.outputs.imageName
output SERVICE_WORKER_IDENTITY_PRINCIPAL_ID string = worker.outputs.identityPrincipalId
output SERVICE_WORKER_NAME string = worker.outputs.name
output SERVICE_WORKER_URI string = worker.outputs.uri
output SERVICE_WORKER_IMAGE_NAME string = worker.outputs.imageName

output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerApps.outputs.registryLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerApps.outputs.registryName

output AZURE_STORAGE_ACCOUNT_NAME string = storage.outputs.name
output AZURE_STORAGE_ACCOUNT_ID string = storage.outputs.id
output AZURE_STORAGE_CONTAINER_NAME string = storage.outputs.containerName
output EXTRACTION_QUEUE_NAME string = storage.outputs.queueName
output AZURE_COSMOS_ACCOUNT_NAME string = cosmos.outputs.name
output AZURE_COSMOS_ACCOUNT_ENDPOINT string = cosmos.outputs.endpoint
output COSMOS_ACCOUNT_ENDPOINT string = cosmos.outputs.endpoint
output COSMOS_DATABASE_NAME string = cosmos.outputs.databaseName
output COSMOS_METADATA_CONTAINER_NAME string = cosmos.outputs.metadataContainerName
output COSMOS_BATCH_REFERENCE_CONTAINER_NAME string = cosmos.outputs.batchReferenceContainerName
output METADATA_STORE_MODE string = metadataStoreMode
output METADATA_READ_FALLBACK string = metadataReadFallback
output APPLICATIONINSIGHTS_NAME string = applicationInsights.outputs.name
output AZURE_OPENAI_ENDPOINT string = azureOpenAiEndpoint
output AZURE_OPENAI_EXTRACTION_DEPLOYMENT string = azureOpenAiExtractionDeployment

// Outputs for SharePoint FilePicker configuration
output ENTRA_CLIENT_ID string = registration.outputs.clientAppId
output ENTRA_TENANT_ID string = tenant().tenantId
