# SharePoint FilePicker Integration

## Overview

This implementation adds SharePoint FilePicker functionality to the CreateTenderModal component, allowing users to browse and select folders from SharePoint for both the tender source path and output location.

## Required Dependencies

Install the following npm packages in the frontend:

```bash
cd frontend
npm install @azure/msal-react @azure/msal-browser uuid
npm install --save-dev @types/uuid
```

## Environment Variables

Add the following environment variables to your deployment:

### Frontend Environment Variables

Create a `.env.local` file in the `frontend` directory for local development:

```bash
# Required for SharePoint FilePicker
VITE_ENTRA_CLIENT_ID=<your-entra-app-client-id>
VITE_ENTRA_TENANT_ID=<your-entra-tenant-id>
VITE_SHAREPOINT_BASE_URL=https://yourtenant.sharepoint.com

# Optional - Backend API URL
VITE_BACKEND_API_URL=/api
```

### Azure Deployment

Update `infra/frontend.bicep` or `infra/aca.bicep` to include the frontend environment variables:

```bicep
env: [
  {
    name: 'VITE_ENTRA_CLIENT_ID'
    value: clientAppId // Pass from registration.outputs.clientAppId
  }
  {
    name: 'VITE_ENTRA_TENANT_ID'
    value: tenantId
  }
  {
    name: 'VITE_SHAREPOINT_BASE_URL'
    value: 'https://yourtenant.sharepoint.com'
  }
]
```

## Files Created/Modified

### New Files

1. **`frontend/src/authConfig.ts`**
   - MSAL configuration
   - Token acquisition logic
   - `getDelegatedToken` function for SharePoint authentication

2. **`frontend/src/components/SharePointFilePicker.tsx`**
   - Reusable SharePoint FilePicker component
   - Handles file/folder selection from SharePoint
   - Manages authentication and messaging with picker window

### Modified Files

1. **`frontend/src/App.tsx`**
   - Added MsalProvider wrapper (conditionally used when MSAL is configured)
   - Initializes MSAL on app start

2. **`frontend/src/components/CreateTenderModal.tsx`**
   - Integrated SharePointFilePicker for both SharePoint Path and Output Location
   - Added handlers for picked files/folders
   - Replaced placeholder button with actual picker

3. **`frontend/src/vite-env.d.ts`**
   - Added type definitions for new environment variables

## How It Works

### Authentication Flow

1. **MSAL Initialization**: When the app starts, MSAL is initialized if `VITE_ENTRA_CLIENT_ID` is configured
2. **Token Acquisition**: When user clicks "Browse", the component requests a delegated token for SharePoint
3. **Silent Authentication**: First attempts silent token acquisition using cached credentials
4. **Interactive Authentication**: Falls back to popup login if silent acquisition fails

### Picker Flow

1. User clicks "Browse" button next to SharePoint Path or Output Location
2. Component opens SharePoint FilePicker in a popup window
3. User authenticates (if needed) and selects a folder
4. Picker returns the selected item's path via `postMessage`
5. Path is automatically populated in the input field

## Features

- **Flexible Configuration**: Works with or without MSAL (gracefully degrades)
- **Folder Selection**: Filters for folders only using `.folder` filter
- **Dual Purpose**: Same component used for both source and output paths
- **User-Friendly**: Visual folder picker instead of manual path entry
- **SharePoint Integration**: Full support for SharePoint sites and OneDrive

## SharePoint Permissions Required

The Entra ID app registration needs the following Microsoft Graph API permissions:

- `User.Read` (Delegated) - Already configured
- `Files.Read.All` (Delegated) - For reading SharePoint files
- `Sites.Read.All` (Delegated) - For accessing SharePoint sites

These can be added in `infra/appregistration.bicep` by updating the `clientAppScopes` parameter.

## Usage Example

```tsx
<SharePointFilePicker
  baseUrl="https://yourtenant.sharepoint.com"
  tenderSitePath="/sites/YourSite/Shared Documents"
  tenderFolder="/Tenders"
  filters={['.folder']}
  onFilePicked={(data) => {
    const path = data.items[0].sharePoint?.path || '';
    setSharepointPath(path);
  }}
  buttonText="Browse"
/>
```

## Testing

### Local Testing (Without SharePoint)

The implementation gracefully handles the case where MSAL is not configured:

```bash
cd frontend
npm run dev
```

The Browse buttons will appear but may not function without proper SharePoint credentials.

### Testing with SharePoint

1. Ensure environment variables are set in `.env.local`
2. Start the frontend: `npm run dev`
3. Click "Create New Tender"
4. Click "Browse" next to SharePoint Path
5. Authenticate if prompted
6. Select a folder from SharePoint
7. Verify the path appears in the input field

## Troubleshooting

### "Failed to get delegated token"
- Verify `VITE_ENTRA_CLIENT_ID` and `VITE_ENTRA_TENANT_ID` are set
- Check that the Entra app registration has the required permissions
- Ensure redirect URIs include your application URL

### "Failed to open picker window"
- Check if popup blockers are enabled
- Ensure the browser allows popups for your site

### "No active account found"
- User may need to sign in first
- The picker will show a popup login if needed

## Future Enhancements

- Add file type filtering for document selection (not just folders)
- Cache recently used paths
- Add validation for SharePoint URLs
- Support for multiple folder selection
- Integration with Microsoft Graph Toolkit for enhanced UI
