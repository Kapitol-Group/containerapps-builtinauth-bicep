targetScope = 'resourceGroup'


@description('Environment name')
param name string
@description('Primary location for all resources')
param location string

@description('Container Apps Environment name')
param containerAppEnvName string
@description('Container Registry name')
param containerRegistryName string
@description('Whether the ACA resource already exists')
param acaExists bool = false
@description('Cosmos DB Account name')
param cosmosDbAccountName string
@description('Chat history database name')
param chatHistoryDatabase string
@description('Chat history container name for KapCoach')
param chatHistoryContainerKapCoach string
@description('Topic history container name for KapCoach')
param topicHistoryContainerKapCoach string

var resourceToken = toLower(uniqueString(subscription().id, name, location))
var tags = { 'azd-env-name': name }
var prefix = toLower('${name}-${resourceToken}')


module logAnalyticsWorkspace 'core/monitor/loganalytics.bicep' = {
  name: 'loganalytics'
  params: {
    name: '${prefix}-loganalytics'
    location: location
    tags: tags
  }
}

module containerRegistry 'core/host/container-registry.bicep' = {
  name: 'containerregistry'
  params: {
    name: containerRegistryName
    location: location
    tags: tags
    workspaceId: logAnalyticsWorkspace.outputs.id
  }
}

module aca 'aca.bicep' = {
  name: 'aca'
  params: {
    name: name
    location: location
    tags: tags
    identityName: '${prefix}-id-aca'
    containerAppsEnvironmentName: containerAppEnvName
    containerRegistryName: containerRegistryName
    logAnalyticsWorkspaceName: logAnalyticsWorkspace.outputs.name
    cosmosDbAccountName: cosmosDbAccountName
    chatHistoryDatabase: chatHistoryDatabase
    chatHistoryContainerKapCoach: chatHistoryContainerKapCoach
    topicHistoryContainerKapCoach: topicHistoryContainerKapCoach
    exists: acaExists
  }
  dependsOn: [
    containerRegistry
  ]
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_CONTAINER_REGISTRY_NAME string = containerRegistry.outputs.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer
output SERVICE_ACA_IDENTITY_PRINCIPAL_ID string = aca.outputs.identityPrincipalId
output SERVICE_ACA_NAME string = aca.outputs.name
output SERVICE_ACA_URI string = aca.outputs.uri
output SERVICE_ACA_IMAGE_NAME string = aca.outputs.imageName