
param name string
param location string = resourceGroup().location
param tags object = {}
param identityName string
param containerAppsEnvironmentName string
param containerRegistryName string
param logAnalyticsWorkspaceName string
param cosmosDbAccountName string
param chatHistoryDatabase string
param chatHistoryContainerKapCoach string
param topicHistoryContainerKapCoach string
param exists bool

@secure()
@description('Optional: Service Principal Client Secret for authentication (bypasses IMDS endpoint)')
param servicePrincipalClientSecret string = ''

@description('Optional: Service Principal Client ID for authentication (bypasses IMDS endpoint)')
param servicePrincipalClientId string = ''

resource acaIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
  tags: tags // Only base tags, no azd-service-name
}

module app 'core/host/container-app-upsert.bicep' = {
  name: 'aca-container-app-module'
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': 'aca' }) // Only container app gets azd-service-name
    identityName: acaIdentity.name
    exists: exists
    containerAppsEnvironmentName: containerAppsEnvironmentName
    containerRegistryName: containerRegistryName
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    env: [
      {
        name: 'AZURE_COSMOSDB_ACCOUNT'
        value: cosmosDbAccountName
      }
      {
        name: 'AZURE_CHAT_HISTORY_DATABASE'
        value: chatHistoryDatabase
      }
      {
        name: 'AZURE_CHAT_HISTORY_CONTAINER_KAPCOACH'
        value: chatHistoryContainerKapCoach
      }
      {
        name: 'AZURE_TOPIC_HISTORY_CONTAINER_KAPCOACH'
        value: topicHistoryContainerKapCoach
      }
      {
        name: 'AZURE_CLIENT_ID'
        value: !empty(servicePrincipalClientId) ? servicePrincipalClientId : acaIdentity.properties.clientId
      }
      {
        name: 'AZURE_TENANT_ID'
        value: tenant().tenantId
      }
      {
        name: 'AZURE_CLIENT_SECRET'
        secretRef: 'azure-client-secret'
      }
    ]
    targetPort: 50505
    secrets: [
      {
        name: 'override-use-mi-fic-assertion-client-id'
        value: acaIdentity.properties.clientId
      }
      {
        name: 'azure-client-secret'
        value: !empty(servicePrincipalClientSecret) ? servicePrincipalClientSecret : 'placeholder'
      }
    ]
  }
}

output identityPrincipalId string = acaIdentity.properties.principalId
output name string = app.outputs.name
output uri string = app.outputs.uri
output imageName string = app.outputs.imageName
output identityResourceId string = app.outputs.identityResourceId