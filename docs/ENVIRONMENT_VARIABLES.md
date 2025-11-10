# Environment Variables Configuration

## Overview

This document describes all environment variables used by the Tender Automation system in both local development and Azure deployment.

## Backend Environment Variables

### Azure Storage Configuration

| Variable | Description | Required | Default | Example |
|----------|-------------|----------|---------|---------|
| `AZURE_STORAGE_ACCOUNT_NAME` | Azure Storage Account name | Yes | - | `myaccount123storage` |
| `AZURE_STORAGE_CONTAINER_NAME` | Blob container for tender documents | No | `tender-documents` | `tender-documents` |

**Notes:**
- In Azure deployment, authentication uses **Managed Identity** (no connection string needed)
- In local development, uses `DefaultAzureCredential` (Azure CLI, VS Code, etc.)
- The backend will warn on startup if `AZURE_STORAGE_ACCOUNT_NAME` is not set

### UiPath Integration Configuration

| Variable | Description | Required | Default | Example |
|----------|-------------|----------|---------|---------|
| `UIPATH_TENANT_NAME` | UiPath Cloud tenant identifier | No* | - | `kapitolgroup` |
| `UIPATH_APP_ID` | OAuth client ID for UiPath Cloud | No* | - | `1234abcd-...` |
| `UIPATH_API_KEY` | OAuth client secret for UiPath Cloud | No* | - | `********************************` |
| `UIPATH_FOLDER_ID` | UiPath organization unit ID (UUID) | No* | - | `a1b2c3d4-...` |
| `UIPATH_QUEUE_NAME` | Target queue name for extraction jobs | No* | - | `TenderExtractionQueue` |
| `UIPATH_MOCK_MODE` | Enable mock mode (no real API calls) | No | `true` | `true` or `false` |

**Notes:**
- \* Required only if `UIPATH_MOCK_MODE=false`
- When `UIPATH_MOCK_MODE=true` (default), the backend returns mock extraction results
- UiPath API key is stored as a **secret** in Azure Container Apps
- **BREAKING CHANGE**: `UIPATH_API_URL` removed - now uses `cloud.uipath.com/{tenant_name}/orchestrator_`
- Credentials use OAuth 2.0 client credentials flow (not simple API key)

### Data Fabric / Entity Store Configuration

| Variable | Description | Required | Default | Example |
|----------|-------------|----------|---------|---------|
| `DATA_FABRIC_API_URL` | Entity Store (Data Fabric) API base URL | Yes** | - | `https://datafabric.example.com` |
| `DATA_FABRIC_API_KEY` | Entity Store API authentication key | Yes** | - | `********************************` |

**Notes:**
- \** Required for Entity Store integration (tender project tracking)
- When missing, Entity Store features disabled but mock mode still works
- API key stored as **secret** in Azure Container Apps

### CORS Configuration

| Variable | Description | Required | Default | Example |
|----------|-------------|----------|---------|---------|
| `FRONTEND_URL` | Allowed CORS origin for frontend | No | `*` | `https://myapp-fe.azurecontainerapps.io` |

**Notes:**
- In production, should be set to specific frontend URL
- Default `*` allows all origins (suitable for development)

## Frontend Environment Variables

### API Configuration

| Variable | Description | Required | Default | Example |
|----------|-------------|----------|---------|---------|
| `VITE_BACKEND_API_URL` | Backend API base URL | No | `/api` | `https://myapp-ca.azurecontainerapps.io/api` |

**Notes:**
- Prefix with `VITE_` to expose to Vite build system
- Default `/api` works with local proxy configuration
- In production, may need full backend URL if not using reverse proxy

## Configuration by Environment

### Local Development

**Backend (.env or shell):**
```bash
# Optional - for local Azure Storage testing
export AZURE_STORAGE_ACCOUNT_NAME=mydevaccount
export AZURE_STORAGE_CONTAINER_NAME=tender-documents

# UiPath - use mock mode
export UIPATH_MOCK_MODE=true

# Data Fabric - optional for local testing
# export DATA_FABRIC_API_URL=https://datafabric.example.com
# export DATA_FABRIC_API_KEY=your-key

# CORS - allow all for dev
export FRONTEND_URL=*
```

**Frontend (.env.local):**
```bash
# Use proxy - no need to set
# VITE_BACKEND_API_URL=/api
```

**Start servers:**
```bash
# Terminal 1 - Backend
source .venv/bin/activate
cd backend
python -m flask run --host 0.0.0.0 --port 50505 --debug

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Azure Deployment

Environment variables are automatically configured via Bicep templates:

**Backend Container App (`infra/aca.bicep`):**
- ✅ `AZURE_STORAGE_ACCOUNT_NAME` - Auto-populated from storage module
- ✅ `AZURE_STORAGE_CONTAINER_NAME` - Set to `tender-documents`
- ✅ `UIPATH_MOCK_MODE` - Set to `true` by default
- ⚠️ `UIPATH_TENANT_NAME`, `UIPATH_APP_ID`, `UIPATH_API_KEY`, `UIPATH_FOLDER_ID`, `UIPATH_QUEUE_NAME` - Must be configured via `azd env set`
- ⚠️ `DATA_FABRIC_API_URL`, `DATA_FABRIC_API_KEY` - Must be configured via `azd env set`

**To configure UiPath in production:**
```bash
# Set environment variables before deployment
azd env set UIPATH_TENANT_NAME "kapitolgroup"
azd env set UIPATH_APP_ID "your-oauth-client-id"
azd env set UIPATH_API_KEY "your-oauth-client-secret"
azd env set UIPATH_FOLDER_ID "your-folder-uuid"
azd env set UIPATH_QUEUE_NAME "TenderExtractionQueue"

# Deploy with new configuration
azd deploy
```

**To configure Entity Store:**
```bash
azd env set DATA_FABRIC_API_URL "https://your-datafabric-url"
azd env set DATA_FABRIC_API_KEY "your-api-key"
azd deploy
```

## Security Best Practices

### ✅ DO:
- Store sensitive values (`UIPATH_API_KEY`) as **secrets** in Container Apps
- Use **Managed Identity** for Azure Storage access (no connection strings)
- Set specific CORS origins in production
- Use environment-specific values (dev/staging/prod)

### ❌ DON'T:
- Commit `.env` files with secrets to git
- Use `CORS: *` in production
- Store connection strings or passwords in code
- Expose internal service URLs publicly

## Troubleshooting

### Issue: "AZURE_STORAGE_ACCOUNT_NAME not set"
**Solution:** 
- Local: Set environment variable before running Flask
- Azure: Verify `main.bicep` passes `storageAccountName` to `aca` module

### Issue: "UiPath integration will not work"
**Solution:**
- Expected if `UIPATH_MOCK_MODE=true` (default)
- To use real UiPath, configure all UiPath variables via `azd env set` and redeploy

### Issue: "Data Fabric credentials not configured"
**Solution:**
- Expected if Entity Store integration not set up
- Configure `DATA_FABRIC_API_URL` and `DATA_FABRIC_API_KEY` via `azd env set` and redeploy
- System will still work in mock mode without Entity Store

### Issue: Frontend can't connect to backend
**Solution:**
- Local: Check backend is running on port 50505
- Azure: Verify `VITE_BACKEND_API_URL` is set correctly in frontend container

### Issue: CORS errors in browser
**Solution:**
- Local: Backend should allow `*` origin by default
- Azure: Set `FRONTEND_URL` to exact frontend URL (no trailing slash)

## Verification Commands

### Check Backend Environment
```bash
# Local
source .venv/bin/activate
cd backend
python -c "import os; print('Storage:', os.getenv('AZURE_STORAGE_ACCOUNT_NAME')); print('UiPath Mock:', os.getenv('UIPATH_MOCK_MODE', 'true'))"

# Azure
az containerapp show -n <backend-app-name> -g <resource-group> --query "properties.template.containers[0].env" -o table
```

### Check Frontend Environment
```bash
# Local
cd frontend
npm run dev
# Check console for API_BASE_URL

# Azure
az containerapp show -n <frontend-app-name> -g <resource-group> --query "properties.template.containers[0].env" -o table
```

### Test API Connection
```bash
# Local backend health
curl http://localhost:50505/api/health

# Azure backend health
curl https://<backend-url>/api/health

# Frontend to backend (from browser console at frontend URL)
fetch('/api/health').then(r => r.json()).then(console.log)
```

---

**Last Updated:** November 2025  
**Related Files:**
- `infra/aca.bicep` - Backend environment configuration
- `infra/main.bicep` - Main infrastructure with UiPath parameters
- `backend/app.py` - Environment variable usage
- `backend/services/uipath_client.py` - UiPath and Entity Store client

**Related Documentation:**
- `UIPATH_ENTITY_STORE_INTEGRATION_PLAN.md` - Implementation plan
- `UIPATH_ENTITY_STORE_IMPLEMENTATION_SUMMARY.md` - Implementation summary
