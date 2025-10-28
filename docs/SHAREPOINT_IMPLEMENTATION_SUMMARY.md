# SharePoint FilePicker Implementation Summary

## ✅ Implementation Complete

The SharePoint FilePicker has been successfully integrated into the CreateTenderModal component.

## 📝 Changes Made

### New Files Created

1. **`frontend/src/authConfig.ts`**
   - MSAL configuration for Azure Entra ID authentication
   - `getDelegatedToken` function for acquiring SharePoint access tokens
   - Conditional MSAL initialization based on environment variables

2. **`frontend/src/components/SharePointFilePicker.tsx`**
   - Reusable SharePoint FilePicker component
   - Handles file/folder selection from SharePoint/OneDrive
   - Manages popup window and message channel communication
   - Supports custom filters and callbacks

3. **`frontend/.env.local.example`**
   - Example environment variable configuration
   - Template for local development setup

4. **`SHAREPOINT_FILEPICKER_IMPLEMENTATION.md`**
   - Comprehensive documentation
   - Setup instructions and troubleshooting guide

5. **`install-sharepoint-deps.sh`**
   - Automated dependency installation script

### Modified Files

1. **`frontend/src/App.tsx`**
   - Added MsalProvider wrapper (conditional)
   - Initializes MSAL on app startup
   - Gracefully handles cases where MSAL is not configured

2. **`frontend/src/components/CreateTenderModal.tsx`**
   - Replaced placeholder "Browse" button with SharePointFilePicker
   - Added for both SharePoint Path and Output Location fields
   - Implemented handlers to populate input fields with selected paths

3. **`frontend/src/vite-env.d.ts`**
   - Added TypeScript definitions for new environment variables:
     - `VITE_ENTRA_CLIENT_ID`
     - `VITE_ENTRA_TENANT_ID`
     - `VITE_SHAREPOINT_BASE_URL`

4. **`infra/appregistration.bicep`**
   - Added SharePoint permissions to clientAppScopes:
     - `Files.Read.All`
     - `Sites.Read.All`

## 🚀 Next Steps

### 1. Install Dependencies

Run the installation script or manually install:

```bash
chmod +x install-sharepoint-deps.sh
./install-sharepoint-deps.sh
```

Or manually:

```bash
cd frontend
npm install @azure/msal-react @azure/msal-browser uuid
npm install --save-dev @types/uuid
```

### 2. Configure Environment Variables

Create `frontend/.env.local` (use `.env.local.example` as template):

```bash
VITE_ENTRA_CLIENT_ID=<from-azure-app-registration>
VITE_ENTRA_TENANT_ID=<your-tenant-id>
VITE_SHAREPOINT_BASE_URL=https://yourtenant.sharepoint.com
```

### 3. Deploy Infrastructure Changes

The updated `appregistration.bicep` with SharePoint permissions needs to be deployed:

```bash
azd up
```

This will update the Entra ID app registration with the required permissions.

### 4. Admin Consent (If Required)

After deployment, an Azure AD administrator may need to grant admin consent for the new permissions:

1. Go to Azure Portal → Entra ID → App Registrations
2. Find your app (e.g., "Tender Automation Client App")
3. Navigate to "API Permissions"
4. Click "Grant admin consent for [Your Organization]"

### 5. Configure Build-Time Environment Variables

⚠️ **Important**: Vite environment variables are **build-time** variables, not runtime variables!

After the first deployment:

```bash
# Get outputs from deployment
azd env get-values

# Set build-time environment variables
azd env set VITE_ENTRA_CLIENT_ID "<value-from-ENTRA_CLIENT_ID>"
azd env set VITE_ENTRA_TENANT_ID "<value-from-ENTRA_TENANT_ID>"  
azd env set VITE_SHAREPOINT_BASE_URL "https://yourtenant.sharepoint.com"

# Redeploy to rebuild frontend with these values
azd deploy
```

**Why two deployments?**
- First deployment creates the Entra app registration and gets the client ID
- Second deployment rebuilds the frontend with the client ID baked in
- Vite variables are compiled into the JavaScript bundle at build time

See [CONTAINER_APP_ENV_VARS.md](./CONTAINER_APP_ENV_VARS.md) for detailed explanation.

## 🧪 Testing

### Local Testing

1. Start the development server:
   ```bash
   cd frontend
   npm run dev
   ```

2. Navigate to the application
3. Click "Create New Tender"
4. Click "Browse" next to SharePoint Path
5. Authenticate if prompted
6. Select a folder from SharePoint
7. Verify the path appears in the input field

### Production Testing

After deploying to Azure:

1. Visit the deployed application URL
2. Test the same flow as local testing
3. Verify authentication works with Azure Entra ID
4. Check browser console for any errors

## 🔧 Key Features

- ✅ **Seamless Integration**: Works with existing Azure Container Apps authentication
- ✅ **Conditional MSAL**: Only activates when environment variables are configured
- ✅ **Graceful Degradation**: App continues to work without MSAL configuration
- ✅ **Dual Purpose**: Same component for both source and output paths
- ✅ **Folder Filtering**: Configured to show only folders (not files)
- ✅ **Token Management**: Handles silent and interactive token acquisition
- ✅ **User-Friendly**: Visual folder picker instead of manual path entry

## 📚 Architecture Decisions

### Why MSAL in Frontend?

Although the backend uses Azure Container Apps built-in authentication, the SharePoint FilePicker requires **client-side tokens** to authenticate with SharePoint. This necessitates MSAL configuration in the frontend specifically for this feature.

### Conditional MSAL Provider

The implementation checks for `VITE_ENTRA_CLIENT_ID` to determine whether to initialize MSAL. This allows the app to:
- Work in environments where SharePoint integration is not needed
- Degrade gracefully if MSAL is not configured
- Maintain backward compatibility

### Token Acquisition Strategy

1. **Silent First**: Attempts to acquire tokens silently using cached credentials
2. **Interactive Fallback**: Shows login popup if silent acquisition fails
3. **Resource-Specific**: Requests tokens for specific SharePoint resources as needed

## 🐛 Troubleshooting

### TypeScript Errors

If you see TypeScript errors about missing modules, ensure dependencies are installed:

```bash
cd frontend
npm install
```

### CORS Issues

If the picker fails to load, verify:
- SharePoint base URL is correct
- App registration redirect URIs include your application URL
- Browser allows popups for your site

### Authentication Failures

Check:
- Environment variables are set correctly
- App registration has required permissions
- Admin consent has been granted (if required)
- User has access to the SharePoint site

## 📖 Related Documentation

- [SHAREPOINT_FILEPICKER_IMPLEMENTATION.md](./SHAREPOINT_FILEPICKER_IMPLEMENTATION.md) - Detailed implementation guide
- [Microsoft Graph File Picker](https://learn.microsoft.com/graph/onedrive-picker) - Official documentation
- [MSAL.js Documentation](https://github.com/AzureAD/microsoft-authentication-library-for-js) - MSAL library reference

## 🎯 Future Enhancements

Potential improvements for future iterations:

- [ ] Support for multiple folder selection
- [ ] File selection (not just folders)
- [ ] Recent paths cache
- [ ] SharePoint URL validation
- [ ] Microsoft Graph Toolkit integration for enhanced UI
- [ ] Breadcrumb navigation in picker
- [ ] Search functionality within picker
- [ ] Custom folder creation from picker

## ✨ Summary

The SharePoint FilePicker implementation provides a professional, user-friendly way to select SharePoint folders for tender management. It integrates seamlessly with Azure Entra ID authentication and maintains compatibility with the existing architecture while adding powerful new functionality.
