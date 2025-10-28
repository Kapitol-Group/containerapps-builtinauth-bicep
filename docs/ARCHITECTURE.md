# SharePoint FilePicker Architecture

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  React Frontend (Vite Build)                               │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  CreateTenderModal.tsx                               │  │ │
│  │  │                                                       │  │ │
│  │  │  [Tender Name        ]                              │  │ │
│  │  │  [SharePoint Path    ] [📁 Browse] ←─┐              │  │ │
│  │  │  [Output Location    ] [📁 Browse] ←─┼─ Pickers     │  │ │
│  │  └──────────────────────────────────────┼──────────────┘  │ │
│  │                                          │                  │ │
│  │  ┌──────────────────────────────────────▼───────────────┐  │ │
│  │  │  SharePointFilePicker.tsx                            │  │ │
│  │  │  • Opens popup window                                │  │ │
│  │  │  • Manages message channels                          │  │ │
│  │  │  • Handles file/folder selection                     │  │ │
│  │  └──────────────────┬───────────────────────────────────┘  │ │
│  │                     │                                       │ │
│  │  ┌──────────────────▼───────────────────────────────────┐  │ │
│  │  │  authConfig.ts (MSAL)                                │  │ │
│  │  │  • getDelegatedToken()                               │  │ │
│  │  │  • Silent token acquisition                          │  │ │
│  │  │  • Interactive fallback (popup)                      │  │ │
│  │  └──────────────────┬───────────────────────────────────┘  │ │
│  │                     │                                       │ │
│  └─────────────────────┼───────────────────────────────────────┘ │
│                        │                                         │
└────────────────────────┼─────────────────────────────────────────┘
                         │
                         │ Token Request
                         ▼
         ┌───────────────────────────────┐
         │   Azure Entra ID              │
         │  • Client ID: xxx-xxx-xxx     │
         │  • Permissions:               │
         │    - Files.Read.All           │
         │    - Sites.Read.All           │
         │    - User.Read                │
         └───────────────┬───────────────┘
                         │
                         │ Access Token
                         ▼
         ┌───────────────────────────────┐
         │   SharePoint Online           │
         │  • Sites & Libraries          │
         │  • Folders & Files            │
         │  • File Picker API            │
         └───────────────────────────────┘
```

---

## 🔄 Authentication Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  1. User clicks "Browse" button                                  │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  2. SharePointFilePicker requests token                          │
│     getDelegatedToken(msalInstance, sharePointUrl)               │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  3. Try silent token acquisition                                 │
│     msalInstance.acquireTokenSilent({...})                       │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                ┌──────┴──────┐
                │             │
         Success│             │Failure
                │             │
                ▼             ▼
    ┌──────────────┐  ┌──────────────────┐
    │ Return token │  │ Show login popup │
    └──────┬───────┘  └────────┬─────────┘
           │                   │
           │                   ▼
           │          ┌──────────────────┐
           │          │ User authenticates│
           │          └────────┬─────────┘
           │                   │
           │                   ▼
           │          ┌──────────────────┐
           │          │ Retry silent     │
           │          │ acquisition      │
           │          └────────┬─────────┘
           │                   │
           └───────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  4. Open SharePoint FilePicker with token                        │
│     window.open() → FilePicker.aspx with access_token            │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  5. User navigates and selects folder                            │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  6. Picker sends selection via postMessage                       │
│     { type: "command", data: { command: "pick", items: [...] }} │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  7. onFilePicked() callback extracts path                        │
│     setSharepointPath(item.sharePoint?.path)                     │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  8. Path appears in input field! ✅                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Build & Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Developer Machine / CI/CD                                       │
│                                                                  │
│  azd deploy                                                      │
│  └─► Sends Docker build context to Azure                        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Azure Container Registry                                        │
│                                                                  │
│  Docker Build Process:                                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Stage 1: Frontend Build                                   │ │
│  │  ┌────────────────────────────────────────────────────┐    │ │
│  │  │  ARG VITE_ENTRA_CLIENT_ID         ◄─ Build args   │    │ │
│  │  │  ARG VITE_ENTRA_TENANT_ID         ◄─ from azd env │    │ │
│  │  │  ARG VITE_SHAREPOINT_BASE_URL     ◄─ variables    │    │ │
│  │  │                                                     │    │ │
│  │  │  npm install                                        │    │ │
│  │  │  npm run build  ◄─ Vite embeds env vars into JS   │    │ │
│  │  │                                                     │    │ │
│  │  │  Output: /frontend/build/* (static files)          │    │ │
│  │  └────────────────────────────────────────────────────┘    │ │
│  │                                                              │ │
│  │  Stage 2: Backend + Frontend                                │ │
│  │  ┌────────────────────────────────────────────────────┐    │ │
│  │  │  Python 3.12                                        │    │ │
│  │  │  pip install -r requirements.txt                    │    │ │
│  │  │  COPY backend/ .                                    │    │ │
│  │  │  COPY --from=frontend-build /frontend/build         │    │ │
│  │  │                                                     │    │ │
│  │  │  Output: Container image with embedded frontend    │    │ │
│  │  └────────────────────────────────────────────────────┘    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Push to ACR: myregistry.azurecr.io/app:latest                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Azure Container Apps                                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Container: myapp-ca                                       │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  Runtime Environment Variables:                      │ │ │
│  │  │  • AZURE_STORAGE_ACCOUNT_NAME (backend)              │ │ │
│  │  │  • UIPATH_API_URL (backend)                          │ │ │
│  │  │  • ... other backend vars ...                        │ │ │
│  │  │                                                       │ │ │
│  │  │  ❌ NOT: VITE_* vars (already compiled in image!)    │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │                                                            │ │
│  │  Serves:                                                   │ │
│  │  • Backend API (Flask) on /api/*                          │ │
│  │  • Frontend static files (React) on /*                    │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Component Dependencies

```
CreateTenderModal.tsx
    │
    ├─► SharePointFilePicker.tsx
    │       │
    │       ├─► authConfig.ts
    │       │       │
    │       │       └─► @azure/msal-browser (npm)
    │       │           @azure/msal-react (npm)
    │       │
    │       └─► uuid (npm)
    │
    └─► api.ts (existing)
            │
            └─► axios (existing)


App.tsx
    │
    ├─► MsalProvider (@azure/msal-react)
    │       │
    │       └─► msalInstance (authConfig.ts)
    │
    └─► Router (react-router-dom)
            │
            ├─► LandingPage
            └─► TenderManagementPage
                    │
                    └─► CreateTenderModal
```

---

## 🔐 Azure Resources & Permissions

```
Azure Subscription
    │
    ├─► Resource Group: RG-{name}
    │   │
    │   ├─► Container Apps Environment
    │   │   └─► Container App: {name}-ca
    │   │       ├─► Backend: Flask + Gunicorn
    │   │       └─► Frontend: React (built static files)
    │   │
    │   ├─► Container Registry
    │   │   └─► Image: {name}/app:latest
    │   │
    │   ├─► Storage Account
    │   │   └─► Container: tender-documents
    │   │
    │   ├─► Log Analytics Workspace
    │   │
    │   └─► Managed Identity
    │       └─► Used for: Storage access, FIC
    │
    └─► Entra ID (Tenant-level)
        └─► App Registration: "Tender Automation Client App"
            ├─► Client ID: {guid} ◄─ Used in frontend
            ├─► Redirect URIs:
            │   • https://{app-url}/.auth/login/aad/callback
            │   • http://localhost:50505/.auth/login/aad/callback
            ├─► Permissions (Delegated):
            │   ├─► User.Read
            │   ├─► Files.Read.All ◄─ For SharePoint files
            │   ├─► Sites.Read.All ◄─ For SharePoint sites
            │   ├─► offline_access
            │   ├─► openid
            │   └─► profile
            └─► Federated Identity Credential
                └─► Subject: Managed Identity
```

---

## 🎯 Data Flow: Folder Selection

```
1. User Action
   [Browse Button Click]
            │
            ▼
2. Component
   SharePointFilePicker.handleClick()
            │
            ├─► Generate channel ID (UUID)
            ├─► Get access token (getDelegatedToken)
            └─► Open popup window
            │
            ▼
3. Popup Window
   FilePicker.aspx (SharePoint)
            │
            ├─► Shows SharePoint sites/folders
            ├─► User navigates folders
            └─► User selects folder
            │
            ▼
4. Message Channel
   postMessage({
     type: "command",
     data: {
       command: "pick",
       items: [{ sharePoint: { path: "/sites/..." } }]
     }
   })
            │
            ▼
5. Component Handler
   messageListener() → onFilePicked()
            │
            ├─► Extract path from items[0]
            └─► setSharepointPath(path)
            │
            ▼
6. UI Update
   [SharePoint Path: /sites/MySite/Docs/Folder]
            │
            ▼
7. Form Submit
   tendersApi.create({
     sharepoint_path: "/sites/MySite/Docs/Folder"
   })
```

---

## 🚀 Deployment Flow

```
Step 1: First Deployment
    azd up
        ├─► Deploy infrastructure (Bicep)
        │   ├─► Create Container Apps Environment
        │   ├─► Create Storage Account
        │   ├─► Create Container Registry
        │   └─► Create App Registration
        │       └─► Outputs: ENTRA_CLIENT_ID ✅
        │
        └─► Build & deploy container
            └─► Build WITHOUT client ID (empty)
                └─► Frontend doesn't have VITE_ENTRA_CLIENT_ID ❌

Step 2: Configure Environment
    azd env set VITE_ENTRA_CLIENT_ID "{client-id}"
    azd env set VITE_ENTRA_TENANT_ID "{tenant-id}"
    azd env set VITE_SHAREPOINT_BASE_URL "https://..."
        │
        └─► Stored in .azure/{env}/.env

Step 3: Second Deployment
    azd deploy
        └─► Rebuild container with build args
            ├─► Docker receives VITE_* as build args
            ├─► Frontend builds with client ID
            └─► Deploy new image
                └─► Frontend HAS VITE_ENTRA_CLIENT_ID ✅

Step 4: Grant Permissions
    Azure Portal → Entra ID → App Registrations
        └─► Grant admin consent for SharePoint permissions

Step 5: Test
    Visit app → Create Tender → Browse
        └─► SharePoint picker works! 🎉
```

---

## 📊 Environment Variables Matrix

| Variable | Set Where | Used When | Type | Required |
|----------|-----------|-----------|------|----------|
| `VITE_ENTRA_CLIENT_ID` | azd env | Docker build | Build-time | Yes |
| `VITE_ENTRA_TENANT_ID` | azd env | Docker build | Build-time | Yes |
| `VITE_SHAREPOINT_BASE_URL` | azd env | Docker build | Build-time | Yes |
| `VITE_BACKEND_API_URL` | azd env | Docker build | Build-time | No (default: /api) |
| `AZURE_STORAGE_ACCOUNT_NAME` | aca.bicep | Container runtime | Runtime | Yes |
| `UIPATH_API_URL` | aca.bicep | Container runtime | Runtime | No |
| `UIPATH_MOCK_MODE` | aca.bicep | Container runtime | Runtime | No (default: true) |

---

This architecture supports:
✅ Secure authentication with Azure Entra ID
✅ SharePoint folder browsing and selection
✅ Container-based deployment
✅ Build-time configuration for frontend
✅ Runtime configuration for backend
✅ Scalable and maintainable design
