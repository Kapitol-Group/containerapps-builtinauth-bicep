@description('Cosmos DB account name')
param cosmosAccountName string

@description('Principal ID to grant Cosmos data access')
param principalId string

// Cosmos DB Built-in Data Contributor role definition ID (SQL RBAC)
var cosmosDataContributorRoleDefinitionId = '00000000-0000-0000-0000-000000000002'

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' existing = {
  name: cosmosAccountName
}

resource cosmosDataContributorAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-04-15' = {
  name: guid(cosmosAccount.id, principalId, cosmosDataContributorRoleDefinitionId)
  parent: cosmosAccount
  properties: {
    principalId: principalId
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${cosmosDataContributorRoleDefinitionId}'
    scope: cosmosAccount.id
  }
}

output roleAssignmentId string = cosmosDataContributorAssignment.id
