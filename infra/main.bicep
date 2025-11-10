targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name which is used to generate a short unique hash for each resource')
param name string

@minLength(1)
@description('Primary location for all resources')
param location string

param acaExists bool = false

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

@description('Data Fabric API URL')
param dataFabricApiUrl string = ''

@secure()
@description('Data Fabric API Key')
param dataFabricApiKey string = ''

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

var resourceToken = toLower(uniqueString(subscription().id, name, location))
var tags = { 'azd-env-name': name }

resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'RG-${name}'
  location: location
  tags: tags
}

var prefix = toLower('${name}-${resourceToken}')

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

// Storage account for tender documents (created first without role assignments)
module storage 'core/storage/storage-account.bicep' = {
  name: 'storage'
  scope: resourceGroup
  params: {
    name: '${take(replace(prefix, '-', ''), 17)}storage'
    location: location
    tags: tags
    isHnsEnabled: true
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
    storageAccountName: storage.outputs.name
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
    customHostName: customHostName
    customCertificateName: customCertificateName
    // Data Fabric configuration
    dataFabricApiUrl: dataFabricApiUrl
    dataFabricApiKey: dataFabricApiKey
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

output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerApps.outputs.registryLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerApps.outputs.registryName

output AZURE_STORAGE_ACCOUNT_NAME string = storage.outputs.name
output AZURE_STORAGE_ACCOUNT_ID string = storage.outputs.id

// Outputs for SharePoint FilePicker configuration
output ENTRA_CLIENT_ID string = registration.outputs.clientAppId
output ENTRA_TENANT_ID string = tenant().tenantId
