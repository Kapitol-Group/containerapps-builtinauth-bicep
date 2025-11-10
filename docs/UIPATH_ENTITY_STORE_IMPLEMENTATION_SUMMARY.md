# UiPath Entity Store Integration Implementation Summary

**Date**: November 10, 2025  
**Status**: Implementation Complete - Ready for Testing

## Overview

Successfully refactored the UiPath client to integrate with the Entity Store (Data Fabric API) and replace direct job submission with queue-based processing using UiPath's bulk queue item addition endpoint.

## Changes Summary

### 1. Infrastructure Updates

#### `infra/aca.bicep`
- **Removed**: `UIPATH_API_URL` environment variable
- **Added**:
  - `UIPATH_TENANT_NAME`: Tenant identifier (e.g., "kapitolgroup")
  - `UIPATH_APP_ID`: OAuth client ID
  - `UIPATH_FOLDER_ID`: Organization unit ID
  - `UIPATH_QUEUE_NAME`: Target queue name
- **Modified**: `UIPATH_API_KEY` now used as OAuth client secret

#### `infra/main.bicep`
- Added parameter declarations for all new UiPath configuration values
- Passed new parameters to `aca` module
- Maintained Data Fabric API configuration (already present)

### 2. Python Dependencies

#### `backend/requirements.txt`
- **Added**: `cuid2==2.0.1` for collision-resistant unique identifiers

### 3. UiPath Client Refactoring

#### `backend/services/uipath_client.py`
Completely rewrote the UiPath client with the following features:

**New Constructor Parameters**:
- `tenant_name`: UiPath tenant
- `app_id`: OAuth client ID
- `api_key`: OAuth client secret
- `folder_id`: Organization unit ID
- `queue_name`: Queue name
- `data_fabric_url`: Entity Store API URL
- `data_fabric_key`: Entity Store API key

**New Methods**:
1. `_authenticate_uipath()`: OAuth 2.0 client credentials authentication
2. `_get_or_create_tender_project()`: Lookup/create TenderProject by name
3. `_get_validation_user()`: Lookup user by email (fail-fast if not found)
4. `_generate_cuid()`: Generate collision-resistant unique IDs
5. `_create_tender_submission()`: Create submission record with CUID reference
6. `_create_tender_file()`: Create file record with QUEUED status
7. `_delete_tender_files()`: Rollback helper for failed submissions
8. `_build_queue_item()`: Build UiPath queue item structure
9. `_bulk_add_queue_items()`: Submit items to UiPath bulk endpoint

**Updated Method**:
- `submit_extraction_job()`: Now performs 6-step workflow with Entity Store integration

**Removed Methods**:
- `_headers()`: No longer needed with OAuth
- `get_job_status()`: Queue-based processing replaces job polling
- `cancel_job()`: Not applicable to queue items

### 4. Backend Integration

#### `backend/app.py`
- **Updated**: UiPathClient instantiation with 7 new parameters
- **Enhanced**: Error handling in `/api/uipath/extract` endpoint:
  - Catches `ValueError` for unregistered users → returns HTTP 400
  - Updates batch metadata with `reference`, `submission_id`, `project_id`
  - Returns new fields in success response

## Data Flow

```
1. API Request → /api/uipath/extract
   ↓
2. Create Batch Metadata (blob storage)
   ↓
3. Entity Store: Query/Create TenderProject
   ↓
4. Entity Store: Validate User (fail if not found)
   ↓
5. Generate CUID Reference
   ↓
6. Entity Store: Create TenderSubmission
   ↓
7. Entity Store: Create TenderFile records (status=QUEUED)
   ↓
8. Build Queue Items (SpecificContent with CUID)
   ↓
9. UiPath OAuth Authentication
   ↓
10. UiPath: BulkAddQueueItems (AllOrNothing)
    ↓
    [SUCCESS] → Return 202 with submission details
    [FAILURE] → Delete TenderFiles → Return 500
```

## Breaking Changes

### API Response Structure
The `/api/uipath/extract` endpoint now returns:
```json
{
  "success": true,
  "data": {
    "batch_id": "batch-xyz",
    "reference": "clxxx...", // NEW: CUID reference
    "submission_id": "uuid", // NEW: Entity Store submission ID
    "project_id": "uuid",    // NEW: Entity Store project ID
    "status": "Queued",
    "batch": { ... }
  }
}
```

**Removed fields**:
- `job_id`: Replaced by `reference` and `submission_id`

### Environment Variables
**Required (must be set for production)**:
- `UIPATH_TENANT_NAME`
- `UIPATH_APP_ID`
- `UIPATH_API_KEY` (now OAuth secret, not API key)
- `UIPATH_FOLDER_ID`
- `UIPATH_QUEUE_NAME`
- `DATA_FABRIC_API_URL`
- `DATA_FABRIC_API_KEY`

**Removed**:
- `UIPATH_API_URL`: No longer used (using cloud.uipath.com)

## Mock Mode Behavior

The client runs in mock mode when:
- Any UiPath credential is missing, OR
- Entity Store credentials are missing

Mock mode returns:
```json
{
  "reference": "mock-clxxx...",
  "submission_id": "mock-submission-id",
  "project_id": "mock-project-id",
  "status": "Queued",
  "tender_id": "...",
  "file_count": 5,
  "submitted_at": "...",
  "submitted_by": "...",
  "batch_id": "...",
  "message": "Mock submission created (UiPath/Entity Store not configured)"
}
```

## Testing Checklist

### Local Testing (Mock Mode)
- [x] Code compiles without syntax errors
- [ ] Backend starts without crashes
- [ ] Mock submission returns expected structure
- [ ] All new fields present in response

### Entity Store Integration
- [ ] TenderProject creation works
- [ ] TenderProject lookup works (existing project)
- [ ] User validation succeeds for valid email
- [ ] User validation fails with 400 for invalid email
- [ ] TenderSubmission creation works
- [ ] TenderFile creation works for multiple files
- [ ] CUID uniqueness verified

### UiPath Integration
- [ ] OAuth authentication succeeds
- [ ] Access token retrieved
- [ ] Queue item structure correct
- [ ] Bulk add payload builds correctly

### End-to-End
- [ ] Submission with valid user succeeds
- [ ] Entity Store records created correctly
- [ ] UiPath queue items added successfully
- [ ] Queue items visible in UiPath Orchestrator
- [ ] SpecificContent fields match expectations

### Error Scenarios
- [ ] Unregistered user returns 400 (no orphaned records)
- [ ] Invalid Entity Store credentials returns 500
- [ ] Invalid UiPath credentials returns 500
- [ ] Queue submission failure triggers TenderFile rollback
- [ ] Project/Submission remain after rollback

## Deployment Instructions

### 1. Set Environment Variables
```bash
# UiPath Configuration
azd env set UIPATH_TENANT_NAME "kapitolgroup"
azd env set UIPATH_APP_ID "<client-id-from-uipath>"
azd env set UIPATH_API_KEY "<client-secret-from-uipath>"
azd env set UIPATH_FOLDER_ID "<folder-uuid>"
azd env set UIPATH_QUEUE_NAME "TenderExtractionQueue"

# Data Fabric Configuration (if not already set)
azd env set DATA_FABRIC_API_URL "https://your-data-fabric-endpoint"
azd env set DATA_FABRIC_API_KEY "<secret-key>"
```

### 2. Deploy
```bash
azd deploy
```

### 3. Verify Deployment
```bash
# Check container logs
azd logs

# Look for startup messages:
# - "UiPath credentials not fully configured" (if mock mode)
# - "Data Fabric credentials not configured" (if Entity Store disabled)
```

## Rollback Strategy

If issues arise, rollback is straightforward:

1. **Revert code changes**: Git reset to previous commit
2. **Restore environment variables**:
   ```bash
   azd env set UIPATH_API_URL "<old-api-url>"
   azd env remove UIPATH_TENANT_NAME
   azd env remove UIPATH_APP_ID
   azd env remove UIPATH_FOLDER_ID
   azd env remove UIPATH_QUEUE_NAME
   ```
3. **Redeploy**: `azd deploy`

## Known Limitations

1. **No Token Caching**: OAuth token fetched on every request (acceptable for low volume)
2. **Synchronous Processing**: Entity Store operations block request thread
3. **No Batch Size Limits**: UiPath bulk endpoint limits not yet validated
4. **Email-Based User Lookup**: Assumes email uniqueness in TitleBlockValidationUsers

## Next Steps

1. **Deploy to Development Environment**
2. **Configure UiPath Credentials** (obtain from UiPath Cloud console)
3. **Register Test Users** in Entity Store TitleBlockValidationUsers table
4. **Submit Test Extraction** with 1-2 files
5. **Verify Entity Store Records** created correctly
6. **Check UiPath Queue** for items with correct SpecificContent
7. **Monitor Logs** for any unexpected errors
8. **Performance Test** with 50+ file submission
9. **Update Documentation** with production configuration details

## Implementation Decisions

### CUID Library
- **Selected**: `cuid2` (implements CUID2 spec with better entropy)
- **Rationale**: More collision-resistant than original CUID

### Queue Priority
- **Fixed**: "High" for all submissions
- **Rationale**: Simple strategy; can be made dynamic later if needed

### Token Caching
- **Decision**: No caching initially
- **Rationale**: Simplicity; reassess if rate limits become issue

### Batch Metadata
- **Decision**: Keep both blob metadata AND Entity Store records
- **Rationale**: Backward compatibility; single source of truth migration can happen later

## Files Modified

1. `infra/aca.bicep` - Environment variable updates
2. `infra/main.bicep` - Parameter additions
3. `backend/requirements.txt` - Added cuid2
4. `backend/services/uipath_client.py` - Complete rewrite
5. `backend/app.py` - Updated instantiation and error handling

## Files Created

1. `docs/UIPATH_ENTITY_STORE_IMPLEMENTATION_SUMMARY.md` (this file)
