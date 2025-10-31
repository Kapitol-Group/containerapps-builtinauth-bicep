targetScope = 'resourceGroup'

@description('Environment name')
param name string
@description('Primary location for all resources')
param location string

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

module aca 'aca.bicep' = {
  name: 'aca'
  params: {
    name: name
    location: location
    tags: tags
    identityName: '${prefix}-id-aca'
    containerAppsEnvironmentName: 'KAP-Scheduler-k6bs5y5rvwus2-containerapps-env'
    containerRegistryName: 'kapschedulerk6bs5y5rvwus2registry'
    exists: false
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output SERVICE_ACA_IDENTITY_PRINCIPAL_ID string = aca.outputs.identityPrincipalId
output SERVICE_ACA_NAME string = aca.outputs.name
output SERVICE_ACA_URI string = aca.outputs.uri
output SERVICE_ACA_IMAGE_NAME string = aca.outputs.imageName