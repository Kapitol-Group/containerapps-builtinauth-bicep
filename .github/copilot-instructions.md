# AI Coding Agent Instructions

## Project Overview

**Construction Tender Automation Platform** - A containerized web application for managing construction tenders with Azure integration. Combines React (Vite) frontend, Flask backend, SharePoint file picker, Azure Blob Storage for document management, and UiPath for drawing metadata extraction.

## Architecture Overview

### Multi-Stage Build Pattern
Single Dockerfile produces combined container:
1. **Stage 1**: Build React frontend with Vite (Node 20) → static files in `/frontend/build`
2. **Stage 2**: Python 3.12 backend copies built frontend to `./frontend_build`, serves via Flask

**Critical**: Frontend environment variables (`VITE_*`) are **build-time only** - embedded during Docker build, not available at runtime. Backend environment variables are runtime.

### Service Boundaries
- **Frontend (React)**: Single-page app with client-side routing, MSAL authentication for SharePoint, served as static files from Flask at `/`
- **Backend (Flask)**: REST API at `/api/*`, serves frontend static files, uses Azure Blob Storage via managed identity
- **Container Apps**: Hosts combined container on port 50505, provides built-in Entra authentication via `X-MS-CLIENT-PRINCIPAL` header

### Key Data Flows
1. **SharePoint File Selection**: Frontend uses MSAL popup → acquires delegated token → opens FilePicker → receives folder path via postMessage
2. **Blob Storage**: Backend uses DefaultAzureCredential (managed identity) → folder structure: `{tender-id}/{category}/{filename}`, tender metadata in `{tender-id}/.tender_metadata`
3. **UiPath Integration**: Backend submits extraction jobs with title block coordinates, polls job status, mock mode enabled by default

## Critical Configuration Patterns

### Environment Variable Matrix

| Variable | Set In | Used When | Type | Impact |
|----------|--------|-----------|------|---------|
| `VITE_ENTRA_CLIENT_ID` | `azd env` → Docker build arg | Frontend build | Build-time | **Must redeploy after changing** |
| `VITE_ENTRA_TENANT_ID` | `azd env` → Docker build arg | Frontend build | Build-time | **Must redeploy after changing** |
| `VITE_SHAREPOINT_BASE_URL` | `azd env` → Docker build arg | Frontend build | Build-time | **Must redeploy after changing** |
| `AZURE_STORAGE_ACCOUNT_NAME` | `aca.bicep` env vars | Backend runtime | Runtime | Can update without rebuild |
| `UIPATH_MOCK_MODE` | `aca.bicep` env vars | Backend runtime | Runtime | Defaults to `'true'` |

**Common Mistake**: Trying to set `VITE_*` vars as Container App environment variables - they must be build args in `azure.yaml`.

### Port Configuration
**Fixed at 50505** across:
- `Dockerfile` EXPOSE directive
- `gunicorn.conf.py` bind setting
- `infra/aca.bicep` targetPort
- `backend/app.py` Flask default

**To change**: Update all 4 locations simultaneously or app won't start.

## Development Workflows

### Local Development (No SharePoint Auth)
```bash
# Backend only
cd backend
python3 -m pip install -r requirements.txt
python3 -m flask run --port 50505 --debug

# Frontend development server (proxies /api to backend via vite.config.ts)
cd frontend
npm install
npm run dev  # Runs on port 3000, proxies /api/* to localhost:50505
```
**Note**: MSAL/SharePoint features won't work locally without configuring `VITE_ENTRA_CLIENT_ID`.
**Proxy Config**: `vite.config.ts` proxies `/api` to backend automatically - no CORS needed in development.

### Deployment with SharePoint Support
```bash
# First deployment (without client ID)
azd up

# Configure frontend build args (CRITICAL STEP)
azd env set VITE_ENTRA_CLIENT_ID "<client-id-from-deployment-output>"
azd env set VITE_ENTRA_TENANT_ID "<tenant-id>"
azd env set VITE_SHAREPOINT_BASE_URL "https://yourtenant.sharepoint.com"

# Redeploy to rebuild with environment variables
azd deploy

# Grant admin consent in Azure Portal:
# Entra ID → App Registrations → <app-name> → API Permissions → Grant admin consent
```

### Two-Stage Deployment Requirement
1. **First `azd up`**: Creates app registration, outputs `ENTRA_CLIENT_ID`
2. **Set env vars**: `azd env set VITE_ENTRA_CLIENT_ID ...`
3. **Second `azd deploy`**: Rebuilds frontend with client ID embedded

## Project-Specific Conventions

### API Response Structure
All API endpoints return:
```json
{
  "success": true/false,
  "data": { ... },      // On success
  "error": "message"    // On failure
}
```
HTTP status codes: 200/201 (success), 400 (validation), 404 (not found), 500 (server error)

### Blob Storage Folder Structure
```
tender-documents/
  {tender-id}/
    .tender_metadata        # Metadata blob with tender info
    {category}/
      {filename}           # Actual files
```
Tender ID: Lowercase, spaces → hyphens (e.g., "Project Alpha" → "project-alpha")

### SharePoint FilePicker Integration
- Component: `frontend/src/components/SharePointFilePicker.tsx`
- Opens popup window to `FilePicker.aspx` with OAuth token
- Uses `postMessage` API with UUID channel ID for communication
- Extracts path from `items[0].sharePoint.path` in pick command
- Requires delegated permissions: `Files.Read.All`, `Sites.Read.All`

### Dual MSAL Instance Pattern
**Critical**: Two separate MSAL instances for different auth scenarios:
1. **SharePoint Picker** (`msalInstance`): Uses build-time `VITE_ENTRA_CLIENT_ID` from `authConfig.ts` - for delegated SharePoint access
2. **Graph API** (`getGraphApiToken()`): Dynamically creates instance from backend `/api/config` endpoint - for Graph API calls

**Why**: Build-time vars embedded in frontend bundle; runtime backend config allows flexibility without rebuild.

### Managed Identity Authentication
Backend uses `DefaultAzureCredential()` - automatically works in Container Apps with managed identity. No connection strings or keys needed for Blob Storage access. Role assignment in `infra/core/storage/storage-role-assignment.bicep`.

## Key Files Reference

### Infrastructure
- `infra/main.bicep`: Subscription-scoped deployment, creates resource group, outputs `ENTRA_CLIENT_ID` for manual setup
- `infra/aca.bicep`: Container app with managed identity, environment variables, secrets (see `allEnvVars` and `allSecrets`)
- `infra/appregistration.bicep`: Creates Entra app with federated credentials, no client secrets
- `azure.yaml`: Defines `aca` service with `remoteBuild: true` and Docker build args from env

### Application
- `backend/app.py`: Flask routes (`/api/*`) + SPA serving (`/` serves `frontend_build/index.html`), 404 handler for client-side routing
- `backend/services/blob_storage.py`: Blob operations using managed identity, tender CRUD, file upload/download
- `backend/services/uipath_client.py`: UiPath REST API client with mock mode fallback
- `frontend/src/authConfig.ts`: MSAL configuration, `getDelegatedToken()` for SharePoint auth with silent → popup fallback
- `Dockerfile`: Multi-stage build accepting `ARG VITE_*` for frontend, copies to `frontend_build/`

## Debugging Patterns

### SharePoint Picker Not Working
1. Check browser console for MSAL errors
2. Verify `VITE_ENTRA_CLIENT_ID` is set (check Network tab → inspect `index.html` for embedded env)
3. Confirm admin consent granted in Entra ID
4. Check popup blocker not blocking FilePicker window

### Blob Storage 403 Errors
1. Verify managed identity role assignment: `az role assignment list --assignee <identity-principal-id>`
2. Check container name matches `AZURE_STORAGE_CONTAINER_NAME` env var
3. Confirm storage account has hierarchical namespace enabled (`infra/core/storage/storage-account.bicep`)

### Container App Won't Start
1. Check logs: `azd logs` or Azure Portal → Log Stream
2. Verify port 50505 exposed and bound in all locations
3. Check Docker build args passed correctly in `azure.yaml`
4. Inspect `gunicorn.conf.py` worker/thread settings (defaults: 4 workers, 8 threads)
5. Gunicorn auto-scales: `(CPU_count * 2) + 1` workers, uses `max_requests=1000` for graceful restarts

### Frontend Shows Old Configuration
**Symptom**: Environment variables not updating after `azd env set`
**Cause**: Frontend vars are build-time, not runtime
**Fix**: Run `azd deploy` to rebuild Docker image with new build args

## Integration Points

### MSAL Authentication Flow
1. App startup: `initializeMsal()` → handle redirect → set active account
2. SharePoint picker click: `getDelegatedToken()` → try silent → fallback to popup
3. Token request scopes: `{resource}/.default` (e.g., `https://tenant.sharepoint.com/.default`)

### UiPath Extraction Job
POST `/api/uipath/extract` with:
- `tender_id`: Target tender
- `file_paths`: Array of blob paths
- `discipline`: Drawing discipline (Architectural, Structural, etc.)
- `title_block_coords`: `{x, y, width, height}` in pixels from PDF preview canvas

Returns job ID, poll GET `/api/uipath/jobs/{job_id}` for status.

### Bicep Deployment Dependencies
Sequence matters:
1. Storage account created first (no role assignments yet)
2. Container app with managed identity
3. Role assignment module grants Storage Blob Data Contributor
4. App registration created
5. App update module configures authentication