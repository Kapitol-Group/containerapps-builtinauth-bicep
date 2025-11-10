# UiPath & Entity Store Configuration Guide

**Last Updated**: November 10, 2025

This guide covers configuring the UiPath Cloud integration and Entity Store (Data Fabric) connection for the Tender Automation system after initial deployment.

## Prerequisites

Before configuring UiPath integration, ensure you have:

1. **Deployed the application** using `azd up`
2. **UiPath Cloud Account** with:
   - Orchestrator access
   - Ability to create OAuth applications
   - Permission to create/manage queues
3. **Entity Store (Data Fabric)** instance with:
   - API endpoint URL
   - API authentication key
   - TenderProject, TenderSubmission, TenderFile, TitleBlockValidationUsers tables configured

## Step 1: Create UiPath OAuth Application

### 1.1 Access UiPath Cloud Admin Console

1. Log in to https://cloud.uipath.com
2. Navigate to **Admin** → **External Applications**
3. Click **Add Application**

### 1.2 Configure Application

**Application Settings:**
- **Application Type**: Confidential Application
- **Application Name**: `Tender Automation API`
- **Grant Type**: Client Credentials
- **Redirect URIs**: Not needed for client credentials flow
- **Scopes**: 
  - `OR.Queues` (Queue management)
  - `OR.Execution` (Process execution)

### 1.3 Save Credentials

After creating the application, save:
- **Client ID** (App ID) - Example: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- **Client Secret** - Example: `AbCdEf123456...` (shown only once - copy immediately!)

### 1.4 Get Organization Details

From the UiPath Cloud portal:

**Tenant Name:**
- Visible in your UiPath URL: `https://cloud.uipath.com/{TENANT_NAME}/`
- Example: `kapitolgroup`

**Folder ID:**
1. Navigate to **Admin** → **Folders**
2. Select the folder where you want queue items processed
3. Click the folder to view details
4. Copy the **Folder ID** (UUID format)
   - Example: `f1a2b3c4-d5e6-7890-1234-567890abcdef`

## Step 2: Create UiPath Queue

### 2.1 Navigate to Orchestrator

1. Go to **Automation** → **Queues**
2. Click **Add Queue**

### 2.2 Configure Queue

**Queue Settings:**
- **Name**: `TenderExtractionQueue` (or your preferred name)
- **Max Number of Retries**: 3
- **Unique Reference**: Yes (use `Reference` field from queue items)
- **Auto Retry**: Yes
- **Enforce Unique Reference**: Yes

**Important**: The queue name must match the `UIPATH_QUEUE_NAME` environment variable.

### 2.3 Verify Queue Created

Queue should appear in the list with status "Active".

## Step 3: Register Validation Users in Entity Store

Before users can submit extraction jobs, they must be registered in the Entity Store `TitleBlockValidationUsers` table.

### 3.1 Access Entity Store

Use your Entity Store management interface or API to add records.

### 3.2 Add User Records

For each user who will submit extraction jobs, create a record:

```json
{
  "UserEmail": "user@example.com"
}
```

**Example users to add:**
```json
[
  {"UserEmail": "john.doe@company.com"},
  {"UserEmail": "jane.smith@company.com"},
  {"UserEmail": "admin@company.com"}
]
```

**Critical**: User lookup is **fail-fast**. If a user tries to submit an extraction job but isn't in this table, the request will return HTTP 400 with "User not registered" error.

## Step 4: Configure Azure Environment Variables

### 4.1 Set UiPath Configuration

```bash
# Navigate to project directory
cd KapitolTenderAutomation

# Set UiPath environment variables
azd env set UIPATH_TENANT_NAME "kapitolgroup"
azd env set UIPATH_APP_ID "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
azd env set UIPATH_API_KEY "AbCdEf123456..."
azd env set UIPATH_FOLDER_ID "f1a2b3c4-d5e6-7890-1234-567890abcdef"
azd env set UIPATH_QUEUE_NAME "TenderExtractionQueue"
```

**Important**: Replace the example values with your actual credentials from Steps 1-2.

### 4.2 Set Entity Store Configuration

```bash
# Set Data Fabric environment variables
azd env set DATA_FABRIC_API_URL "https://your-datafabric-api.example.com"
azd env set DATA_FABRIC_API_KEY "your-entity-store-api-key"
```

**Note**: Obtain these from your Entity Store/Data Fabric administrator.

### 4.3 Verify Configuration

```bash
# View configured environment variables (secrets masked)
azd env get-values
```

Expected output should include:
```
UIPATH_TENANT_NAME="kapitolgroup"
UIPATH_APP_ID="a1b2c3d4-..."
UIPATH_API_KEY="***"  # Masked
UIPATH_FOLDER_ID="f1a2b3c4-..."
UIPATH_QUEUE_NAME="TenderExtractionQueue"
DATA_FABRIC_API_URL="https://..."
DATA_FABRIC_API_KEY="***"  # Masked
```

## Step 5: Redeploy Application

### 5.1 Deploy with New Configuration

```bash
# Redeploy to apply environment variable changes
azd deploy
```

This will:
1. Update Container App environment variables
2. Inject secrets securely
3. Restart containers with new configuration

### 5.2 Monitor Deployment

```bash
# Watch deployment logs
azd monitor --logs
```

### 5.3 Verify Startup

Check logs for successful configuration:

```
UiPath credentials not fully configured  # Should NOT appear
Data Fabric credentials not configured   # Should NOT appear
```

If you see these warnings, environment variables weren't set correctly.

## Step 6: Test Integration

### 6.1 Register Test User

Ensure your test user email is in `TitleBlockValidationUsers` table (Step 3).

### 6.2 Submit Test Extraction

Using the frontend UI or API:

```bash
curl -X POST https://your-app.azurecontainerapps.io/api/uipath/extract \
  -H "Content-Type: application/json" \
  -d '{
    "tender_id": "test-project-001",
    "file_paths": ["test-project-001/drawings/sheet-01.pdf"],
    "destination": "Architectural",
    "title_block_coords": {"x": 50, "y": 50, "width": 300, "height": 100}
  }'
```

### 6.3 Verify Success Response

Expected response (HTTP 202):
```json
{
  "success": true,
  "data": {
    "batch_id": "batch-...",
    "reference": "clxxxx...",
    "submission_id": "uuid-...",
    "project_id": "uuid-...",
    "status": "Queued"
  }
}
```

### 6.4 Check UiPath Queue

1. Log in to UiPath Cloud
2. Navigate to **Automation** → **Queues** → **TenderExtractionQueue**
3. You should see a new queue item with:
   - **Reference**: The CUID from response
   - **Status**: New
   - **Specific Content**: Contains ProjectName, ValidationUser, FilePath, etc.

### 6.5 Check Entity Store Records

Verify records were created:

**TenderProject:**
- Name = "test-project-001"

**TenderSubmission:**
- ProjectId = (ID from TenderProject)
- Reference = (CUID from API response)
- SubmittedBy = (User from TitleBlockValidationUsers)

**TenderFile:**
- SubmissionId = (ID from TenderSubmission)
- OriginalPath = "test-project-001/drawings/sheet-01.pdf"
- Status = 1 (QUEUED)

## Troubleshooting

### Error: "User not registered in TitleBlockValidationUsers"

**Cause**: Submitted user email not in Entity Store table.

**Solution**:
1. Check exact email format (case-sensitive)
2. Add user to TitleBlockValidationUsers table (Step 3)
3. Retry submission

### Error: "UiPath authentication failed"

**Cause**: Invalid OAuth credentials or permissions.

**Solution**:
1. Verify `UIPATH_APP_ID` and `UIPATH_API_KEY` are correct
2. Check OAuth application has required scopes (`OR.Queues`)
3. Ensure OAuth application is enabled in UiPath
4. Re-generate client secret if compromised

### Error: "Failed to submit queue items to UiPath"

**Possible Causes**:
- Queue name doesn't exist
- Folder ID incorrect
- Insufficient permissions

**Solution**:
1. Verify queue exists in UiPath (Step 2)
2. Check `UIPATH_QUEUE_NAME` matches actual queue name (exact match)
3. Verify `UIPATH_FOLDER_ID` matches the folder containing the queue
4. Check OAuth application has `OR.Queues` scope

### Warning: "Mock submission created"

**Cause**: Running in mock mode (credentials not fully configured).

**Solution**:
1. Verify all 5 UiPath environment variables are set (Step 4.1)
2. Redeploy with `azd deploy`
3. Check startup logs for credential warnings

### Entity Store Connection Fails

**Symptoms**:
- "Failed to get/create TenderProject" errors
- "Failed to lookup validation user" errors

**Solution**:
1. Verify `DATA_FABRIC_API_URL` is accessible from Container App
2. Check `DATA_FABRIC_API_KEY` is valid
3. Ensure Entity Store tables exist with correct schemas
4. Check network connectivity (firewall rules, private endpoints)

## Security Considerations

### Credential Storage

- **OAuth Client Secret**: Stored as Container App secret (encrypted at rest)
- **Entity Store API Key**: Stored as Container App secret (encrypted at rest)
- **Never commit credentials to Git**: Use `azd env set` or Azure Key Vault

### Network Security

- **Outbound Requirements**:
  - `cloud.uipath.com` (TCP 443) - UiPath OAuth and API
  - Your Entity Store endpoint (TCP 443)
- **Inbound**: Container App public endpoint (can be restricted via Bicep)

### Least Privilege

- UiPath OAuth app should have **only** required scopes
- Entity Store API key should have **minimum** permissions:
  - Read: TenderProject, TitleBlockValidationUsers
  - Write: TenderProject, TenderSubmission, TenderFile
  - Delete: TenderFile (for rollback)

## Rollback Procedure

If integration causes issues:

### Option 1: Revert to Mock Mode

```bash
# Keep integration configured but disable temporarily
azd env set UIPATH_MOCK_MODE "true"
azd deploy
```

### Option 2: Remove Configuration

```bash
# Remove UiPath configuration
azd env remove UIPATH_TENANT_NAME
azd env remove UIPATH_APP_ID
azd env remove UIPATH_API_KEY
azd env remove UIPATH_FOLDER_ID
azd env remove UIPATH_QUEUE_NAME

# Redeploy
azd deploy
```

System will automatically fall back to mock mode.

## Production Checklist

Before enabling in production:

- [ ] UiPath OAuth application created with client credentials flow
- [ ] Client secret securely stored (backed up in secure location)
- [ ] Queue created in UiPath Orchestrator
- [ ] Queue name matches `UIPATH_QUEUE_NAME` exactly
- [ ] All production users registered in `TitleBlockValidationUsers`
- [ ] Entity Store connection tested and verified
- [ ] Test submission completed successfully end-to-end
- [ ] Queue item appeared in UiPath Orchestrator
- [ ] Entity Store records created correctly
- [ ] Logs reviewed for errors or warnings
- [ ] Rollback plan documented and tested
- [ ] Monitoring/alerting configured for failed queue items

## Additional Resources

- [UiPath Cloud OAuth Documentation](https://docs.uipath.com/orchestrator/docs/managing-external-applications)
- [UiPath Queue API Reference](https://docs.uipath.com/orchestrator/reference)
- [Environment Variables Documentation](./ENVIRONMENT_VARIABLES.md)
- [Implementation Summary](./UIPATH_ENTITY_STORE_IMPLEMENTATION_SUMMARY.md)

---

**Need Help?**
- Check `azd monitor --logs` for detailed error messages
- Review Entity Store logs for API call failures
- Contact UiPath support for Orchestrator/queue issues
