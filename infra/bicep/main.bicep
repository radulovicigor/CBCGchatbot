// Bicep template za Azure infrastrukturu
// Reference: https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/

@description('Environment name')
param environment string = 'dev'

@description('Azure region')
param location string = 'northeurope'

@description('App name prefix')
param appName string = 'cbcgbot'

@description('Azure Search SKU')
param searchSku string = 'basic'

@description('App Service SKU')
param appServiceSku string = 'F1'

@description('Functions SKU')
param functionsSku string = 'Y1'

var resourceGroupName = 'rg-${appName}-${environment}'
var searchServiceName = 'search-${appName}-${environment}'
var appServiceName = 'app-${appName}-${environment}'
var functionsName = 'func-${appName}-${environment}'
var storageName = 'st${replace(appName, '-', '')}${environment}'
var keyVaultName = 'kv-${appName}-${environment}'

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  sku: {
    name: searchSku
  }
  properties: {
    hostingMode: 'default'
    partitionCount: 1
    replicaCount: 1
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    supportsHttpsTrafficOnly: true
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: []
    enabledForDeployment: true
    enabledForDiskEncryption: true
    enabledForTemplateDeployment: true
  }
}

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: 'plan-${appName}-${environment}'
  location: location
  sku: {
    name: appServiceSku
  }
}

// App Service (FastAPI)
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: appServiceName
  location: location
  kind: 'app'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      appSettings: [
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'true'
        }
      ]
    }
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionsName
  location: location
  kind: 'functionapp'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: storage.properties.primaryEndpoints.blob
        }
      ]
    }
  }
}

output searchEndpoint string = search.properties.serviceUrl
output appServiceUrl string = 'https://${appServiceName}.azurewebsites.net'
output functionsUrl string = 'https://${functionsName}.azurewebsites.net'

