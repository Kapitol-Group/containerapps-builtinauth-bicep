@description('Cosmos DB account name')
param name string

@description('Deployment location')
param location string = resourceGroup().location

@description('Tags for resources')
param tags object = {}

@description('Cosmos SQL database name')
param databaseName string = 'kapitol-tender-automation'

@description('Metadata container name')
param metadataContainerName string = 'metadata'

@description('Batch reference index container name')
param batchReferenceContainerName string = 'batch-reference-index'

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: name
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    disableLocalAuth: true
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
}

resource sqlDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  parent: cosmosAccount
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

resource metadataContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: sqlDatabase
  name: metadataContainerName
  properties: {
    resource: {
      id: metadataContainerName
      partitionKey: {
        paths: [
          '/tender_id'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
  }
}

resource batchReferenceContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: sqlDatabase
  name: batchReferenceContainerName
  properties: {
    resource: {
      id: batchReferenceContainerName
      partitionKey: {
        paths: [
          '/reference'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
  }
}

output id string = cosmosAccount.id
output name string = cosmosAccount.name
output endpoint string = cosmosAccount.properties.documentEndpoint
output databaseName string = sqlDatabase.name
output metadataContainerName string = metadataContainer.name
output batchReferenceContainerName string = batchReferenceContainer.name
