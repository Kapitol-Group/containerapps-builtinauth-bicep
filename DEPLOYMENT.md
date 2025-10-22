# Deployment Guide - Construction Tender Automation

## Prerequisites

1. **Azure Subscription**: Active Azure subscription with contributor access
2. **Azure CLI**: Version >= 2.49.0
   ```bash
   az --version
   az login
   ```
3. **Azure Developer CLI**: Latest version
   ```bash
   azd version
   azd auth login
   ```
4. **Node.js**: Version 20.x
5. **Python**: Version 3.12+

## Quick Deployment

### Option 1: Azure Developer CLI (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd KapitolTenderAutomation

# Login to Azure
azd auth login

# Provision infrastructure and deploy services
azd up

# Follow prompts:
# - Environment name: e.g., "tender-prod"
# - Azure subscription: Select your subscription
# - Location: e.g., "eastus"
```

The `azd up` command will:
1. Create resource group
2. Provision Azure Container Apps environment
3. Create Azure Container Registry
4. Provision Azure Blob Storage with hierarchical namespace
5. Create managed identities for both services
6. Build Docker images remotely in ACR
7. Deploy frontend and backend containers
8. Configure networking and ingress

### Option 2: Manual Deployment

#### Step 1: Create Resources

```bash
# Set variables
LOCATION="eastus"
ENV_NAME="tender-prod"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Deploy Bicep template
az deployment sub create \
  --location $LOCATION \
  --template-file infra/main.bicep \
  --parameters name=$ENV_NAME location=$LOCATION
```

#### Step 2: Get Resource Names

```bash
# Get outputs
RESOURCE_GROUP="RG-$ENV_NAME"
REGISTRY_NAME=$(az deployment sub show \
  --name main \
  --query properties.outputs.AZURE_CONTAINER_REGISTRY_NAME.value -o tsv)
STORAGE_NAME=$(az deployment sub show \
  --name main \
  --query properties.outputs.AZURE_STORAGE_ACCOUNT_NAME.value -o tsv)
```

#### Step 3: Build and Push Images

```bash
# Build backend
az acr build \
  --registry $REGISTRY_NAME \
  --image backend:latest \
  ./backend

# Build frontend
az acr build \
  --registry $REGISTRY_NAME \
  --image frontend:latest \
  ./frontend
```

#### Step 4: Configure Managed Identity Permissions

```bash
# Get backend managed identity
BACKEND_IDENTITY=$(az deployment sub show \
  --name main \
  --query properties.outputs.SERVICE_ACA_IDENTITY_PRINCIPAL_ID.value -o tsv)

# Grant Storage Blob Data Contributor role
az role assignment create \
  --assignee $BACKEND_IDENTITY \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_NAME"
```

## Post-Deployment Configuration

### 1. Configure Environment Variables

#### Backend Service
The following are automatically configured via Bicep:
- `AZURE_STORAGE_ACCOUNT_NAME`: Set from deployment outputs

#### Additional Configuration Needed

```bash
# Get backend container app name
BACKEND_APP=$(az deployment sub show \
  --name main \
  --query properties.outputs.SERVICE_ACA_NAME.value -o tsv)

# Add UiPath configuration (if available)
az containerapp secret set \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --secrets uipath-api-key=<your-uipath-api-key>

az containerapp update \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    "UIPATH_API_URL=<your-uipath-url>" \
    "UIPATH_API_KEY=secretref:uipath-api-key"
```

#### Frontend Service

```bash
# Get frontend container app name
FRONTEND_APP=$(az deployment sub show \
  --name main \
  --query properties.outputs.SERVICE_FRONTEND_NAME.value -o tsv)

# Get backend URL
BACKEND_URL=$(az deployment sub show \
  --name main \
  --query properties.outputs.SERVICE_ACA_URI.value -o tsv)

# Update frontend environment
az containerapp update \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars "REACT_APP_BACKEND_API_URL=$BACKEND_URL"
```

### 2. Optional: Enable Authentication

The Bicep templates include commented-out Entra ID authentication. To enable:

1. Uncomment the app registration section in `infra/main.bicep`
2. Run deployment again:
   ```bash
   azd up
   ```
3. Follow the post-deployment instructions for app registration setup

## Verification Steps

### 1. Check Deployment Status

```bash
# View all deployed resources
az resource list --resource-group $RESOURCE_GROUP --output table

# Check container app status
az containerapp show \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --query properties.runningStatus -o tsv

az containerapp show \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --query properties.runningStatus -o tsv
```

### 2. Test Endpoints

```bash
# Get frontend URL
FRONTEND_URL=$(az containerapp show \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "Frontend: https://$FRONTEND_URL"

# Get backend URL
BACKEND_URL=$(az containerapp show \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "Backend: https://$BACKEND_URL"

# Test backend health
curl "https://$BACKEND_URL/api/health"
```

### 3. View Logs

```bash
# Backend logs
az containerapp logs show \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --tail 50

# Frontend logs
az containerapp logs show \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --tail 50
```

## Monitoring and Troubleshooting

### View Application Insights

```bash
# Get Application Insights connection string
az monitor app-insights component show \
  --app <app-insights-name> \
  --resource-group $RESOURCE_GROUP \
  --query connectionString -o tsv
```

### Common Issues

#### Issue: Container app not starting

**Solution**: Check logs
```bash
az containerapp logs show \
  --name <app-name> \
  --resource-group $RESOURCE_GROUP \
  --tail 100
```

#### Issue: 403 Forbidden on blob storage

**Solution**: Verify managed identity permissions
```bash
# List role assignments
az role assignment list \
  --assignee $BACKEND_IDENTITY \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_NAME"
```

#### Issue: CORS errors in frontend

**Solution**: Check backend CORS configuration
```bash
# Update backend to allow frontend origin
az containerapp update \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars "FRONTEND_URL=https://$FRONTEND_URL"
```

## Updating the Application

### Update Backend Code

```bash
# Using azd
azd deploy aca

# Or manually
az acr build \
  --registry $REGISTRY_NAME \
  --image backend:latest \
  ./backend

az containerapp update \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --image "$REGISTRY_NAME.azurecr.io/backend:latest"
```

### Update Frontend Code

```bash
# Using azd
azd deploy frontend

# Or manually
az acr build \
  --registry $REGISTRY_NAME \
  --image frontend:latest \
  ./frontend

az containerapp update \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --image "$REGISTRY_NAME.azurecr.io/frontend:latest"
```

## Cleanup

### Remove All Resources

```bash
# Using azd
azd down

# Or manually
az group delete --name $RESOURCE_GROUP --yes --no-wait
```

## Production Considerations

1. **Scaling**: Configure autoscaling rules
   ```bash
   az containerapp update \
     --name $BACKEND_APP \
     --resource-group $RESOURCE_GROUP \
     --min-replicas 2 \
     --max-replicas 10
   ```

2. **Custom Domain**: Add custom domain
   ```bash
   az containerapp hostname add \
     --name $FRONTEND_APP \
     --resource-group $RESOURCE_GROUP \
     --hostname <your-domain>
   ```

3. **SSL Certificate**: Bind managed certificate
   ```bash
   az containerapp ssl upload \
     --name $FRONTEND_APP \
     --resource-group $RESOURCE_GROUP \
     --certificate-file <cert-path> \
     --hostname <your-domain>
   ```

4. **Monitoring**: Configure alerts
   ```bash
   # Create metric alert for high CPU
   az monitor metrics alert create \
     --name high-cpu-alert \
     --resource-group $RESOURCE_GROUP \
     --scopes <container-app-resource-id> \
     --condition "avg UsagePercentage > 80" \
     --window-size 5m \
     --evaluation-frequency 1m
   ```

## Support

For issues or questions:
- Check `PROJECT_STATUS.md` for known limitations
- Review Azure Portal logs and metrics
- Contact DevOps team

## Next Steps

After successful deployment:
1. Configure UiPath API credentials
2. Set up SharePoint FilePicker integration
3. Enable Entra ID authentication
4. Configure custom domain and SSL
5. Set up monitoring and alerts
6. Train users on the system
