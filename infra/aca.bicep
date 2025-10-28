param name string
param location string = resourceGroup().location
param tags object = {}

param identityName string
param containerAppsEnvironmentName string
param containerRegistryName string
param serviceName string = 'aca'
param exists bool

// Environment variables for the backend
param storageAccountName string = ''
param uipathApiUrl string = ''
param uipathApiKey string = ''
param uipathTenantName string = ''
param uipathFolderId string = ''
param uipathMockMode string = 'true'

// Frontend configuration parameters
param entraClientId string = ''
param entraTenantId string = ''
param sharePointBaseUrl string = ''

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
    name: 'AZURE_STORAGE_ACCOUNT_NAME'
    value: storageAccountName
  }
  {
    name: 'AZURE_STORAGE_CONTAINER_NAME'
    value: 'tender-documents'
  }
  {
    name: 'UIPATH_API_URL'
    value: uipathApiUrl
  }
  {
    name: 'UIPATH_TENANT_NAME'
    value: uipathTenantName
  }
  {
    name: 'UIPATH_FOLDER_ID'
    value: uipathFolderId
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
]

var uipathApiKeyEnvVar = !empty(uipathApiKey)
  ? [
      {
        name: 'UIPATH_API_KEY'
        secretRef: 'uipath-api-key'
      }
    ]
  : []

var allEnvVars = concat(baseEnvVars, uipathApiKeyEnvVar)

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

var allSecrets = concat(baseSecrets, uipathApiKeySecret)

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
    env: allEnvVars
    targetPort: 50505
    secrets: allSecrets
  }
}

output identityPrincipalId string = acaIdentity.properties.principalId
output name string = app.outputs.name
output uri string = app.outputs.uri
output imageName string = app.outputs.imageName
output identityResourceId string = app.outputs.identityResourceId
