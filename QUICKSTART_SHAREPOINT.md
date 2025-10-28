# SharePoint FilePicker Quick Start

## 🚀 Quick Setup (3 steps)

### 1. Install Dependencies
```bash
./install-sharepoint-deps.sh
```

### 2. Configure Environment
```bash
cd frontend
cp .env.local.example .env.local
# Edit .env.local with your values
```

### 3. Deploy Infrastructure (Two-Stage Deployment)

**First deployment:**
```bash
azd up
```

**Configure frontend build variables:**
```bash
# Get the outputs
azd env get-values

# Set the build-time variables
azd env set VITE_ENTRA_CLIENT_ID "<ENTRA_CLIENT_ID-value>"
azd env set VITE_ENTRA_TENANT_ID "<ENTRA_TENANT_ID-value>"
azd env set VITE_SHAREPOINT_BASE_URL "https://yourtenant.sharepoint.com"
```

**Second deployment:**
```bash
azd deploy
```

💡 **Why two deployments?** Vite variables are build-time only. First deployment creates the app registration, second deployment rebuilds with the client ID.

## 📋 Required Values

Get these from Azure Portal:

| Variable | Where to Find |
|----------|---------------|
| `VITE_ENTRA_CLIENT_ID` | Azure Portal → Entra ID → App Registrations → Your App → Application (client) ID |
| `VITE_ENTRA_TENANT_ID` | Azure Portal → Entra ID → Overview → Tenant ID |
| `VITE_SHAREPOINT_BASE_URL` | Your SharePoint URL (e.g., `https://contoso.sharepoint.com`) |

## ✅ What's Implemented

- ✅ SharePoint folder picker in CreateTenderModal
- ✅ Works for both "SharePoint Path" and "Output Location"
- ✅ MSAL authentication integration
- ✅ Token acquisition (silent + interactive fallback)
- ✅ Graceful degradation if not configured
- ✅ Updated Bicep with required permissions

## 🧪 Test It

1. Start dev server: `cd frontend && npm run dev`
2. Click "Create New Tender"
3. Click "Browse" button
4. Select a folder from SharePoint
5. Path auto-fills in the input field

## 📖 Need More Info?

- **Detailed Guide**: [SHAREPOINT_FILEPICKER_IMPLEMENTATION.md](./SHAREPOINT_FILEPICKER_IMPLEMENTATION.md)
- **Summary**: [SHAREPOINT_IMPLEMENTATION_SUMMARY.md](./SHAREPOINT_IMPLEMENTATION_SUMMARY.md)
- **Troubleshooting**: See documentation files above

## 🐛 Common Issues

**"Cannot find module '@azure/msal-browser'"**
→ Run `./install-sharepoint-deps.sh`

**"Failed to get delegated token"**
→ Check `.env.local` has correct CLIENT_ID and TENANT_ID

**Picker won't open**
→ Allow popups for your site in browser settings

**Permissions error**
→ Run `azd up` to deploy updated app registration with SharePoint permissions
