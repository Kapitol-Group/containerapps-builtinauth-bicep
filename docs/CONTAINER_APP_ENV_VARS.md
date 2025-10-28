# Container App Environment Variables for SharePoint FilePicker

## Understanding Build-Time vs Runtime Environment Variables

### Vite Environment Variables (Build-Time)

Vite environment variables (`VITE_*`) are **build-time** variables that are embedded into the JavaScript bundle during the `npm run build` process. They are NOT runtime environment variables.

This means:
- ✅ They must be available when Docker builds the frontend
- ✅ They are baked into the compiled JavaScript files
- ❌ They cannot be changed after the container is built
- ❌ Setting them as container app environment variables won't work

### Backend Environment Variables (Runtime)

Backend Python environment variables are **runtime** variables that the Flask app reads when it starts. These are set in `infra/aca.bicep` and can be changed without rebuilding.

## How to Set SharePoint FilePicker Environment Variables

Since the frontend uses Vite, we need to pass the variables as **Docker build arguments**.

### Option 1: Using azd Environment Variables (Recommended)

1. **After first deployment**, get the Client ID:
   ```bash
   azd env get-values
   # Look for ENTRA_CLIENT_ID and ENTRA_TENANT_ID
   ```

2. **Set azd environment variables** for the build:
   ```bash
   azd env set VITE_ENTRA_CLIENT_ID "your-client-id-here"
   azd env set VITE_ENTRA_TENANT_ID "your-tenant-id-here"
   azd env set VITE_SHAREPOINT_BASE_URL "https://yourtenant.sharepoint.com"
   ```

3. **Redeploy** to rebuild with the new values:
   ```bash
   azd deploy
   ```

### Option 2: Using .env File (Local Development)

For local development with `azd` that respects `.env` files:

1. Create `.azure/<environment-name>/.env`:
   ```bash
   VITE_ENTRA_CLIENT_ID=your-client-id-here
   VITE_ENTRA_TENANT_ID=your-tenant-id-here
   VITE_SHAREPOINT_BASE_URL=https://yourtenant.sharepoint.com
   ```

2. Deploy:
   ```bash
   azd deploy
   ```

### Option 3: Using azure.yaml Docker Options

Update `azure.yaml` to pass build args (requires azd configuration):

```yaml
services:
  aca:
    project: .
    language: py
    host: containerapp
    docker:
      remoteBuild: true
      path: ./Dockerfile
      buildArgs:
        - VITE_ENTRA_CLIENT_ID=${VITE_ENTRA_CLIENT_ID}
        - VITE_ENTRA_TENANT_ID=${VITE_ENTRA_TENANT_ID}
        - VITE_SHAREPOINT_BASE_URL=${VITE_SHAREPOINT_BASE_URL}
```

## Complete Deployment Workflow

### First Deployment (Without SharePoint FilePicker)

```bash
# Initial deployment - creates infrastructure and app registration
azd up
```

At this point:
- ✅ Container app is running
- ✅ Entra app registration is created
- ❌ SharePoint FilePicker won't work (no client ID in frontend)

### Second Deployment (Enable SharePoint FilePicker)

```bash
# Get the client ID and tenant ID from deployment outputs
azd env get-values

# Set the environment variables for frontend build
azd env set VITE_ENTRA_CLIENT_ID "<value-from-ENTRA_CLIENT_ID>"
azd env set VITE_ENTRA_TENANT_ID "<value-from-ENTRA_TENANT_ID>"
azd env set VITE_SHAREPOINT_BASE_URL "https://yourtenant.sharepoint.com"

# Redeploy to rebuild frontend with the values
azd deploy
```

Now:
- ✅ Frontend is rebuilt with client ID
- ✅ SharePoint FilePicker will work
- ✅ Users can browse SharePoint folders

## Alternative: Two-Stage azure.yaml

You can also configure `azure.yaml` to automatically set these from infrastructure outputs:

```yaml
name: containerapps-builtinauth-bicep
services:
  aca:
    project: .
    language: py
    host: containerapp
    docker:
      remoteBuild: true
      path: ./Dockerfile
      buildArgs:
        - VITE_ENTRA_CLIENT_ID=${ENTRA_CLIENT_ID}
        - VITE_ENTRA_TENANT_ID=${ENTRA_TENANT_ID}
        - VITE_SHAREPOINT_BASE_URL=${VITE_SHAREPOINT_BASE_URL:-https://yourtenant.sharepoint.com}
```

With this configuration:
1. First `azd up` creates infrastructure and outputs `ENTRA_CLIENT_ID` and `ENTRA_TENANT_ID`
2. Second `azd deploy` uses those outputs as build args automatically
3. You only need to set `VITE_SHAREPOINT_BASE_URL` manually:
   ```bash
   azd env set VITE_SHAREPOINT_BASE_URL "https://yourtenant.sharepoint.com"
   ```

## Dockerfile Build Arguments

The `Dockerfile` has been updated to accept these build arguments:

```dockerfile
# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build

ARG VITE_ENTRA_CLIENT_ID
ARG VITE_ENTRA_TENANT_ID
ARG VITE_SHAREPOINT_BASE_URL
ARG VITE_BACKEND_API_URL=/api

ENV VITE_ENTRA_CLIENT_ID=$VITE_ENTRA_CLIENT_ID
ENV VITE_ENTRA_TENANT_ID=$VITE_ENTRA_TENANT_ID
ENV VITE_SHAREPOINT_BASE_URL=$VITE_SHAREPOINT_BASE_URL
ENV VITE_BACKEND_API_URL=$VITE_BACKEND_API_URL

# ... rest of build process
```

## Infrastructure Outputs

The `infra/main.bicep` now outputs the required values:

```bicep
output ENTRA_CLIENT_ID string = registration.outputs.clientAppId
output ENTRA_TENANT_ID string = tenant().tenantId
```

These are automatically stored in `azd` environment and can be referenced.

## Verification

After redeployment, verify the values are embedded in the frontend:

1. Visit your container app URL
2. Open browser Developer Tools → Console
3. Run:
   ```javascript
   console.log(import.meta.env.VITE_ENTRA_CLIENT_ID)
   ```
4. You should see your client ID (not `undefined`)

## Troubleshooting

### "VITE_ENTRA_CLIENT_ID is undefined"
- The build arguments weren't passed during Docker build
- Redeploy with correct `azd env` variables set

### "Failed to get delegated token"
- Check that the client ID is correct
- Verify app registration permissions include SharePoint scopes
- Check that admin consent has been granted

### "Need to rebuild after changing variables"
- Remember: Vite variables are build-time only
- Any change requires a rebuild: `azd deploy`
- Runtime container app environment variables won't affect frontend

## Summary

**Key Points:**
1. ✅ Dockerfile updated with build arguments for `VITE_*` variables
2. ✅ Infrastructure outputs `ENTRA_CLIENT_ID` and `ENTRA_TENANT_ID`
3. ✅ Use `azd env set` to configure build-time variables
4. ✅ Redeploy after setting variables to rebuild frontend
5. ❌ Don't set `VITE_*` variables in `aca.bicep` (won't work for frontend)
