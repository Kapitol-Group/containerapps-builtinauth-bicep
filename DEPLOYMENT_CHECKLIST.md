# Deployment Checklist

## ✅ Pre-Deployment (COMPLETED)

- [x] **Backend Code Complete**
  - [x] Flask REST API with 13 endpoints
  - [x] Blob Storage service with managed identity
  - [x] UiPath client with mock mode
  - [x] Authentication utilities
  - [x] Dependencies installed (Flask 3.1.2, Azure SDK, etc.)

- [x] **Frontend Code Complete**
  - [x] React components (8 .tsx files)
  - [x] Pages (LandingPage, TenderManagementPage)
  - [x] API client with typed methods
  - [x] TypeScript types defined
  - [x] Migrated to Vite 6.4.0
  - [x] Production build successful (269 KB)

- [x] **Infrastructure Code Complete**
  - [x] Bicep templates for dual-service architecture
  - [x] Azure Blob Storage configuration
  - [x] Container Apps with managed identity
  - [x] Application Insights monitoring
  - [x] Frontend container app configuration

- [x] **Documentation Complete**
  - [x] PROJECT_STATUS.md - Implementation details
  - [x] DEPLOYMENT.md - Deployment guide
  - [x] QUICKSTART.md - Developer setup
  - [x] IMPLEMENTATION_SUMMARY.md - Overview
  - [x] VITE_MIGRATION.md - Build system migration

## 🚀 Deployment Steps

### Step 1: Azure CLI Authentication
```bash
azd auth login
```
**Expected Result:** Browser opens, sign in with Azure credentials

### Step 2: Initialize Environment (First Time Only)
```bash
azd env new <environment-name>
# Example: azd env new dev
```

### Step 3: Deploy to Azure
```bash
azd up
```

**What This Does:**
1. Provisions Azure resources (Container Apps, Storage Account, etc.)
2. Builds Docker images remotely in Azure Container Registry
3. Deploys containers to Azure Container Apps
4. Configures managed identity and authentication
5. Sets up Application Insights monitoring

**Expected Duration:** 10-15 minutes

### Step 4: Verify Deployment
```bash
# Get deployment URLs
azd env get-values | grep URI

# View logs
azd logs --service backend
azd logs --service frontend
```

## 📋 Post-Deployment Configuration

### Required Configuration

1. **UiPath API Credentials** (if using real UiPath)
   - Navigate to Azure Portal → Container Apps → backend → Environment Variables
   - Add secrets:
     - `UIPATH_API_KEY`
     - `UIPATH_TENANT_NAME`
     - `UIPATH_FOLDER_ID`
   - Remove or set `UIPATH_MOCK_MODE=false`

2. **Storage Account Access**
   - Verify managed identity has "Storage Blob Data Contributor" role
   - Create initial container: `tender-documents`

### Optional Configuration

3. **Entra ID Authentication** (currently disabled)
   - Uncomment app registration section in `infra/main.bicep` (line 71+)
   - Update federated credentials
   - Redeploy with `azd up`

4. **SharePoint Integration** (Phase 4)
   - Register Microsoft Graph app
   - Add credentials to backend environment
   - Update `CreateTenderModal.tsx` with FilePicker SDK

5. **Custom Domain**
   - Configure custom domain in Azure Portal
   - Update CORS settings in backend

## 🧪 Testing Checklist

### After Deployment

- [ ] **Frontend Accessible**
  - [ ] Navigate to frontend URL
  - [ ] Landing page loads
  - [ ] No console errors

- [ ] **Backend API Health**
  - [ ] Visit `<backend-url>/api/health`
  - [ ] Returns 200 OK with system info

- [ ] **Tender Management**
  - [ ] Create new tender
  - [ ] View tender list
  - [ ] Delete tender

- [ ] **File Operations**
  - [ ] Upload file (drag-and-drop)
  - [ ] Upload file (click browse)
  - [ ] View file in browser
  - [ ] Download file
  - [ ] Update file category
  - [ ] Delete file

- [ ] **UiPath Integration** (if configured)
  - [ ] Queue extraction job
  - [ ] Check job status
  - [ ] Verify results

## 🐛 Troubleshooting

### Issue: Frontend shows "Cannot connect to backend"
**Solution:** 
- Check CORS settings in `backend/app.py`
- Verify backend URL in Azure Portal
- Check backend logs: `azd logs --service backend`

### Issue: "Authentication failed" errors in logs
**Solution:**
- Verify managed identity is assigned to backend container app
- Check Storage Account IAM roles
- Restart container app

### Issue: Files not uploading
**Solution:**
- Check container `tender-documents` exists in Storage Account
- Verify hierarchical namespace is enabled
- Check managed identity has "Storage Blob Data Contributor" role

### Issue: Build fails during `azd up`
**Solution:**
- Check Docker build logs in Azure Portal
- Verify all dependencies in requirements.txt/package.json are valid
- Check for syntax errors with: `cd backend && python3 -m py_compile app.py`

## 📊 Monitoring

### Application Insights
- Navigate to Azure Portal → Application Insights
- View:
  - Live Metrics (real-time traffic)
  - Failures (errors and exceptions)
  - Performance (response times)
  - Availability (uptime monitoring)

### Container App Logs
```bash
# Stream logs
azd logs --service backend --follow
azd logs --service frontend --follow

# Or in Azure Portal
# Container Apps → <app-name> → Log stream
```

### Storage Metrics
- Azure Portal → Storage Account → Monitoring
- Check:
  - Transaction count
  - Ingress/Egress data
  - Success rate

## 🔐 Security Checklist

- [x] **Managed Identity** - No secrets in code
- [ ] **HTTPS Only** - Container Apps default (verify in portal)
- [ ] **CORS Configuration** - Update for production domains
- [ ] **API Rate Limiting** - Consider adding
- [ ] **Input Validation** - Backend validates all inputs
- [ ] **File Size Limits** - Currently set to 50MB in nginx
- [ ] **Entra ID Auth** - Optional, currently disabled

## 📈 Performance Benchmarks

### Expected Performance
- **Frontend Load Time:** <2 seconds
- **API Response Time:** <500ms (except file operations)
- **File Upload:** ~1-2 seconds per MB
- **Build Time:** ~5-10 minutes (first deployment)
- **Scale:** 0-10 replicas (Container Apps autoscaling)

### Optimization Opportunities
- Enable CDN for static assets
- Add Redis cache for frequent queries
- Implement lazy loading for file lists
- Add pagination for large tender lists

## 🎯 Success Criteria

✅ **Deployment Successful When:**
1. Both frontend and backend URLs accessible
2. User can create tender
3. User can upload file
4. File appears in Azure Blob Storage
5. No authentication errors in logs
6. Application Insights receiving telemetry

---

**Current Status:** 🟢 **READY FOR DEPLOYMENT**  
**Build Status:** ✅ All builds passing  
**Documentation:** ✅ Complete  
**Next Action:** Run `azd auth login && azd up`
