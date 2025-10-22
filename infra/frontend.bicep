@description('The name of the container app')
param name string

@description('Location for resources')
param location string = resourceGroup().location

@description('Tags for resources')
param tags object = {}

@description('Name of the user assigned identity for the app')
param identityName string

@description('Name of the container apps environment')
param containerAppsEnvironmentName string

@description('Name of the container registry')
param containerRegistryName string

@description('Exists flag for container app')
param exists bool

@description('Service name')
param serviceName string = 'frontend'

@description('Backend API URL')
param backendApiUrl string

resource frontendIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
  tags: tags
}

module app 'core/host/container-app-upsert.bicep' = {
  name: '${serviceName}-container-app-module'
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    identityName: frontendIdentity.name
    exists: exists
    containerAppsEnvironmentName: containerAppsEnvironmentName
    containerRegistryName: containerRegistryName
    env: [
      {
        name: 'BACKEND_API_URL'
        value: backendApiUrl
      }
    ]
    targetPort: 80
    secrets: [
      {
        name: 'override-use-mi-fic-assertion-client-id'
        value: frontendIdentity.properties.clientId
      }
    ]
  }
}

output identityPrincipalId string = frontendIdentity.properties.principalId
output name string = app.outputs.name
output uri string = app.outputs.uri
output imageName string = app.outputs.imageName
output identityResourceId string = app.outputs.identityResourceId
