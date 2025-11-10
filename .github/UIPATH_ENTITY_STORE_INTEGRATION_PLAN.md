---
title: UiPath Entity Store Integration & Queue-Based Submission
version: 1.0
date_created: 2025-11-09
last_updated: 2025-11-09
---
# Implementation Plan: UiPath Entity Store Integration & Queue-Based Submission

Refactor the UiPath client to integrate with the Entity Store (Data Fabric API) for tracking tender projects, submissions, and files. Replace the current job submission mechanism with UiPath's bulk queue item addition endpoint using OAuth client credentials authentication.

## Architecture and Design

### Overview
The new architecture introduces a **data persistence layer** through the Entity Store before submitting extraction jobs to UiPath. This ensures:
- **Traceability**: All tender submissions and files are tracked in a centralized data store
- **Consistency**: Collision-resistant unique identifiers (CUIDs) link submissions across systems
- **Queue-based processing**: UiPath processes files from queue items rather than direct job submissions
- **Fail-fast validation**: User lookup fails immediately if not registered in the system

### Component Interactions

```
┌─────────────────────────────────────────────────────────────────┐
│ Flask Backend (app.py)                                          │
│  POST /api/uipath/extract                                       │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ UiPath Client (uipath_client.py)                                │
│  submit_extraction_job()                                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 1. Query TenderProject by Name (tender_id)             │    │
│  │    - If not found: Create new TenderProject            │    │
│  └────────────────────────────────────────────────────────┘    │
│                      │                                          │
│                      ▼                                          │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 2. Query TitleBlockValidationUsers by UserEmail        │    │
│  │    - If not found: FAIL submission immediately         │    │
│  └────────────────────────────────────────────────────────┘    │
│                      │                                          │
│                      ▼                                          │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 3. Generate CUID reference                             │    │
│  │    Create TenderSubmission with:                       │    │
│  │    - project_id (from step 1)                          │    │
│  │    - reference (CUID)                                  │    │
│  │    - submitted_by (from step 2)                        │    │
│  │    - validated_by (from step 2)                        │    │
│  │    - archive_name: "n/a"                               │    │
│  │    - is_addendum: false                                │    │
│  └────────────────────────────────────────────────────────┘    │
│                      │                                          │
│                      ▼                                          │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 4. For each file_path:                                 │    │
│  │    - Create TenderFile with:                           │    │
│  │      • submission_id (from step 3)                     │    │
│  │      • original_path (blob storage path)               │    │
│  │      • original_filename (extracted from path)         │    │
│  │      • status: TenderProcessStatus.QUEUED              │    │
│  │    - Build queue item object with SpecificContent      │    │
│  │    - Add to queue_items list                           │    │
│  └────────────────────────────────────────────────────────┘    │
│                      │                                          │
│                      ▼                                          │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 5. Authenticate with UiPath OAuth                      │    │
│  │    POST /identity_/connect/token                       │    │
│  │    - client_credentials grant                          │    │
│  └────────────────────────────────────────────────────────┘    │
│                      │                                          │
│                      ▼                                          │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 6. Bulk add queue items                                │    │
│  │    POST /odata/Queues/UiPathODataSvc.BulkAddQueueItems│    │
│  │    - queueName: UIPATH_QUEUE_NAME                      │    │
│  │    - commitType: AllOrNothing                          │    │
│  │    - queueItems: [...]                                 │    │
│  │                                                         │    │
│  │    If FAILS: Delete all TenderFile records created     │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
           ▲                                    ▲
           │                                    │
   Entity Store API                      UiPath Cloud API
   (DATA_FABRIC_API_URL)                (cloud.uipath.com)
```

### Data Flow

1. **Tender Project Lookup/Creation**: Check if tender project exists by `Name` field (equals `tender_id`). If not found, create new project.

2. **User Validation**: Query `TitleBlockValidationUsers` by `UserEmail` (equals `submitted_by`). **Critical**: Fail immediately if user not found (no default/fallback).

3. **Submission Creation**: Create `TenderSubmission` record with CUID reference that links the submission across both Entity Store and UiPath queue items.

4. **File Tracking**: Create individual `TenderFile` records with `status=QUEUED` before queue submission. Store blob storage paths (e.g., `{tender-id}/{category}/{filename}`).

5. **Queue Item Structure**: Each file gets a queue item with `SpecificContent` containing:
   - `ProjectName`: tender_id
   - `ValidationUser`: submitted_by (email)
   - `FilePath`: Blob storage path
   - `Reference`: CUID (links back to TenderSubmission)
   - `DocumentCount`: Total files in submission
   - `RequestDate`: Current date (yyyy-MM-dd format)
   - `IsAddendum`: false

6. **Bulk Submission**: All queue items submitted atomically (`commitType: AllOrNothing`) to UiPath endpoint.

7. **Rollback on Failure**: If bulk queue add fails, delete all created `TenderFile` records. Leave `TenderProject` and `TenderSubmission` intact for manual cleanup/investigation.

### Environment Variable Changes

**New variables added:**
- `UIPATH_TENANT_NAME`: UiPath tenant identifier (e.g., "kapitolgroup")
- `UIPATH_APP_ID`: OAuth client ID for UiPath authentication
- `UIPATH_API_KEY`: OAuth client secret (stored as secret in Bicep)
- `UIPATH_FOLDER_ID`: Organization unit ID (UUID format)
- `UIPATH_QUEUE_NAME`: Target queue name for extraction jobs

**Removed variables:**
- `UIPATH_API_URL`: No longer needed (using cloud.uipath.com with tenant-specific paths)

**Retained variables:**
- `UIPATH_MOCK_MODE`: Keep for development/testing without real UiPath/Entity Store

### Authentication Methods

**Entity Store (Data Fabric API):**
- `AuthenticatedClient` with bearer token
- Base URL: `DATA_FABRIC_API_URL` environment variable
- Token: `DATA_FABRIC_API_KEY` environment variable

**UiPath Cloud:**
- OAuth 2.0 client credentials flow
- Token endpoint: `https://cloud.uipath.com/identity_/connect/token`
- Grant type: `client_credentials`
- Credentials: `UIPATH_APP_ID` + `UIPATH_API_KEY`
- Token cached per request (not persistent across requests initially)

### Error Handling Strategy

| Failure Point | Action | Rollback | Response |
|--------------|--------|----------|----------|
| TenderProject creation fails | Fail submission | None needed | HTTP 500, error details |
| User not found in TitleBlockValidationUsers | Fail submission immediately | None needed | HTTP 400, "User not registered" |
| TenderSubmission creation fails | Fail submission | None needed | HTTP 500, error details |
| TenderFile creation fails (any) | Fail submission | None needed | HTTP 500, error details |
| UiPath OAuth fails | Fail submission | None needed | HTTP 500, "Authentication failed" |
| Bulk queue add fails | Delete created TenderFiles | Leave Project & Submission | HTTP 500, "Queue submission failed" |

**Rationale:** Entity Store records provide audit trail even on failure. Only TenderFile records are deleted on queue failure since they represent "processing intent" that didn't materialize.

## Tasks

### Phase 1: Infrastructure & Configuration
- [ ] **Task 1.1**: Update `infra/aca.bicep` to add new environment variables
  - [ ] Add `UIPATH_TENANT_NAME` to baseEnvVars array
  - [ ] Add `UIPATH_APP_ID` to baseEnvVars array  
  - [ ] Add `UIPATH_FOLDER_ID` to baseEnvVars array
  - [ ] Add `UIPATH_QUEUE_NAME` to baseEnvVars array
  - [ ] Update `uipathApiKeySecret` to use `UIPATH_API_KEY` (rename if needed)
  - [ ] Remove `UIPATH_API_URL` from baseEnvVars (no longer needed)

- [ ] **Task 1.2**: Update parameter declarations in `infra/aca.bicep`
  - [ ] Add `param uipathTenantName string = ''`
  - [ ] Add `param uipathAppId string = ''`
  - [ ] Add `param uipathApiKey string = ''` (already exists, verify)
  - [ ] Add `param uipathFolderId string = ''`
  - [ ] Add `param uipathQueueName string = ''`
  - [ ] Remove `param uipathApiUrl string = ''` (if exists)

- [ ] **Task 1.3**: Update `infra/main.bicep` to pass new parameters to aca module
  - [ ] Add uipathTenantName parameter and pass to aca module
  - [ ] Add uipathAppId parameter and pass to aca module
  - [ ] Add uipathFolderId parameter and pass to aca module
  - [ ] Add uipathQueueName parameter and pass to aca module
  - [ ] Remove uipathApiUrl references

### Phase 2: Python Dependencies
- [ ] **Task 2.1**: Add required Python packages to `backend/requirements.txt`
  - [ ] Add `cuid2` package for CUID generation (or `pycuid2`)
  - [ ] Verify entity-store-transformation-client is already listed
  - [ ] Verify `requests` package exists (for UiPath OAuth)

- [ ] **Task 2.2**: Install and test dependencies locally
  - [ ] Run `pip install -r backend/requirements.txt` in dev environment
  - [ ] Verify imports work: `from cuid import cuid` (or equivalent)
  - [ ] Verify entity store client imports work

### Phase 3: UiPath Client Refactoring
- [ ] **Task 3.1**: Update UiPathClient `__init__` method
  - [ ] Add parameters: `tenant_name`, `app_id`, `api_key`, `folder_id`, `queue_name`
  - [ ] Store all as instance variables
  - [ ] Remove `base_url` parameter and instance variable
  - [ ] Update mock mode detection logic (check if `tenant_name` and `app_id` are set)

- [ ] **Task 3.2**: Add Entity Store client initialization
  - [ ] Add `data_fabric_url` and `data_fabric_key` parameters to `__init__`
  - [ ] Create `AuthenticatedClient` instance as `self.entity_client`
  - [ ] Store for use throughout the class

- [ ] **Task 3.3**: Implement UiPath OAuth authentication method
  - [ ] Create `_authenticate_uipath()` method
  - [ ] POST to `https://cloud.uipath.com/identity_/connect/token`
  - [ ] Send form-urlencoded data: `client_id`, `client_secret`, `grant_type=client_credentials`
  - [ ] Parse JSON response and extract `access_token`
  - [ ] Return bearer token string
  - [ ] Add error handling with descriptive messages
  - [ ] Add logging for auth success/failure

- [ ] **Task 3.4**: Implement helper method to lookup/create TenderProject
  - [ ] Create `_get_or_create_tender_project(tender_id: str) -> TenderProject` method
  - [ ] Use `query_tender_project.sync()` from entity store client
  - [ ] Build QueryRequest with filter: `Name == tender_id`
  - [ ] If found (records > 0): Return first record
  - [ ] If not found: Call `add_tender_project.sync()` with `TenderProject(name=tender_id)`
  - [ ] Return created project with ID
  - [ ] Add logging for create vs. found scenarios
  - [ ] Add error handling with descriptive messages

- [ ] **Task 3.5**: Implement helper method to lookup validation user
  - [ ] Create `_get_validation_user(user_email: str) -> TitleBlockValidationUsers` method
  - [ ] Use `query_title_block_validation_users.sync()` from entity store client
  - [ ] Build QueryRequest with filter: `UserEmail == user_email`
  - [ ] If found: Return first record
  - [ ] If NOT found: Raise `ValueError(f"User {user_email} not registered in TitleBlockValidationUsers")`
  - [ ] Add logging for lookup result
  - [ ] Add error handling

- [ ] **Task 3.6**: Implement CUID generation helper
  - [ ] Create `_generate_cuid() -> str` method
  - [ ] Use cuid library to generate collision-resistant unique ID
  - [ ] Return as string
  - [ ] Add comment explaining purpose (links submission to queue items)

- [ ] **Task 3.7**: Implement TenderSubmission creation helper
  - [ ] Create `_create_tender_submission(project: TenderProject, reference: str, user: TitleBlockValidationUsers) -> TenderSubmission` method
  - [ ] Build `TenderSubmission` object with:
    - `project_id=project` (pass TenderProject object)
    - `reference=reference` (CUID string)
    - `submitted_by=user` (TitleBlockValidationUsers object)
    - `validated_by=user` (same user for now)
    - `archive_name="n/a"`
    - `is_addendum=False`
  - [ ] Call `add_tender_submission.sync()` from entity store client
  - [ ] Return created submission with ID
  - [ ] Add logging for submission creation
  - [ ] Add error handling

- [ ] **Task 3.8**: Implement TenderFile creation helper
  - [ ] Create `_create_tender_file(submission: TenderSubmission, file_path: str) -> TenderFile` method
  - [ ] Extract filename from file_path (split on '/' and take last element)
  - [ ] Build `TenderFile` object with:
    - `submission_id=submission` (pass TenderSubmission object)
    - `original_path=file_path` (full blob storage path)
    - `original_filename=filename` (extracted filename)
    - `status=TenderProcessStatus.QUEUED`
  - [ ] Call `add_tender_file.sync()` from entity store client
  - [ ] Return created TenderFile with ID
  - [ ] Add logging for file creation
  - [ ] Add error handling

- [ ] **Task 3.9**: Implement TenderFile deletion helper (for rollback)
  - [ ] Create `_delete_tender_files(file_ids: List[UUID]) -> None` method
  - [ ] Use `batch_delete_tender_file.sync()` from entity store client
  - [ ] Pass list of file IDs to delete
  - [ ] Add logging for deletion count
  - [ ] Add error handling (log but don't raise - this is cleanup)

- [ ] **Task 3.10**: Implement queue item builder helper
  - [ ] Create `_build_queue_item(file_path: str, tender_id: str, submitted_by: str, reference: str, document_count: int) -> Dict` method
  - [ ] Build dictionary structure:
    ```python
    {
        "Name": self.queue_name,
        "Priority": "High",
        "SpecificContent": {
            "ProjectName": tender_id,
            "ValidationUser": submitted_by,
            "FilePath": file_path,
            "Reference": reference,
            "DocumentCount": document_count,
            "RequestDate": datetime.now().strftime("%Y-%m-%d"),
            "IsAddendum": False
        }
    }
    ```
  - [ ] Return dictionary
  - [ ] Add logging for queue item creation

- [ ] **Task 3.11**: Implement bulk queue add method
  - [ ] Create `_bulk_add_queue_items(queue_items: List[Dict]) -> Dict` method
  - [ ] Get OAuth token via `self._authenticate_uipath()`
  - [ ] Build request URL: `https://cloud.uipath.com/kapitolgroup/{self.tenant_name}/orchestrator_/odata/Queues/UiPathODataSvc.BulkAddQueueItems`
  - [ ] Build headers:
    - `Authorization: Bearer {token}`
    - `Content-Type: application/json`
    - `X-UIPATH-OrganizationUnitId: {self.folder_id}`
  - [ ] Build payload:
    ```python
    {
        "queueName": self.queue_name,
        "commitType": "AllOrNothing",
        "queueItems": queue_items
    }
    ```
  - [ ] POST request with 30s timeout
  - [ ] Check response status (raise on error)
  - [ ] Parse and return JSON response
  - [ ] Add comprehensive logging
  - [ ] Add error handling with descriptive messages

- [ ] **Task 3.12**: Refactor `submit_extraction_job()` method
  - [ ] **Step 1**: Check mock mode - if enabled, return existing mock response
  - [ ] **Step 2**: Call `_get_or_create_tender_project(tender_id)` → store as `project`
  - [ ] **Step 3**: Call `_get_validation_user(submitted_by)` → store as `user` (this can raise ValueError)
  - [ ] **Step 4**: Generate CUID via `_generate_cuid()` → store as `reference`
  - [ ] **Step 5**: Call `_create_tender_submission(project, reference, user)` → store as `submission`
  - [ ] **Step 6**: Loop through `file_paths`:
    - Call `_create_tender_file(submission, file_path)` → append to `created_files` list
    - Call `_build_queue_item(file_path, tender_id, submitted_by, reference, len(file_paths))` → append to `queue_items` list
  - [ ] **Step 7**: Wrap bulk add in try/except:
    - Try: Call `_bulk_add_queue_items(queue_items)` → store response
    - Except: Extract file IDs from `created_files`, call `_delete_tender_files(file_ids)`, then re-raise
  - [ ] **Step 8**: Build return response with submission details
  - [ ] Update return structure to include `reference`, `submission_id`, `project_id`
  - [ ] Add comprehensive logging throughout
  - [ ] Ensure all errors propagate with context

- [ ] **Task 3.13**: Update mock mode logic
  - [ ] Update mock response to include new fields: `reference`, `submission_id`, `project_id`
  - [ ] Ensure mock mode doesn't require Entity Store or UiPath credentials
  - [ ] Add mock CUID generation for consistency

- [ ] **Task 3.14**: Remove old methods
  - [ ] Remove `_headers()` method (no longer using base_url pattern)
  - [ ] Remove `get_job_status()` method (replaced by queue-based tracking)
  - [ ] Remove `cancel_job()` method (not applicable to queue items)
  - [ ] Update any imports/references

### Phase 4: Backend Integration
- [ ] **Task 4.1**: Update UiPathClient instantiation in `backend/app.py`
  - [ ] Locate client initialization (likely near top of file or in route)
  - [ ] Update constructor call with new parameters:
    - `tenant_name=os.getenv('UIPATH_TENANT_NAME')`
    - `app_id=os.getenv('UIPATH_APP_ID')`
    - `api_key=os.getenv('UIPATH_API_KEY')`
    - `folder_id=os.getenv('UIPATH_FOLDER_ID')`
    - `queue_name=os.getenv('UIPATH_QUEUE_NAME')`
    - `data_fabric_url=os.getenv('DATA_FABRIC_API_URL')`
    - `data_fabric_key=os.getenv('DATA_FABRIC_API_KEY')`
  - [ ] Remove `base_url` parameter
  - [ ] Test client instantiation doesn't crash

- [ ] **Task 4.2**: Update error handling in `/api/uipath/extract` endpoint
  - [ ] Add specific catch for `ValueError` (user not found) → return HTTP 400
  - [ ] Update existing exception handling to include context from new errors
  - [ ] Ensure rollback errors are logged but don't mask original error
  - [ ] Update response messages to be user-friendly

- [ ] **Task 4.3**: Update response structure in `/api/uipath/extract` endpoint
  - [ ] Include `reference` (CUID) in success response
  - [ ] Include `submission_id` in success response
  - [ ] Include `project_id` in success response
  - [ ] Keep `batch_id` if batch metadata is still being created
  - [ ] Update HTTP status code to 202 (Accepted) on success
  - [ ] Update response documentation/comments

- [ ] **Task 4.4**: Remove deprecated endpoints/logic
  - [ ] Check if `/api/uipath/jobs/{job_id}` endpoint exists → remove or update docs
  - [ ] Check if job status polling is referenced → remove or update
  - [ ] Update any frontend references to job tracking

### Phase 5: Testing & Validation
- [ ] **Task 5.1**: Local testing with mock mode
  - [ ] Set `UIPATH_MOCK_MODE=true`
  - [ ] Test submission flow without real credentials
  - [ ] Verify mock response includes all new fields
  - [ ] Check logs for proper flow execution

- [ ] **Task 5.2**: Entity Store integration testing
  - [ ] Set `DATA_FABRIC_API_URL` and `DATA_FABRIC_API_KEY` environment variables
  - [ ] Test TenderProject creation with new tender_id
  - [ ] Test TenderProject lookup with existing tender_id
  - [ ] Test user lookup with valid user email
  - [ ] Test user lookup with INVALID user email → verify 400 error
  - [ ] Test TenderSubmission creation
  - [ ] Test TenderFile creation for multiple files
  - [ ] Verify CUID uniqueness across submissions

- [ ] **Task 5.3**: UiPath integration testing (with mock queue initially)
  - [ ] Set all UiPath environment variables
  - [ ] Test OAuth authentication flow
  - [ ] Verify token retrieval and format
  - [ ] Test queue item structure building
  - [ ] Test bulk add payload construction

- [ ] **Task 5.4**: End-to-end integration testing
  - [ ] Submit real extraction job with valid user
  - [ ] Verify all Entity Store records created correctly
  - [ ] Verify queue items added to UiPath queue
  - [ ] Check queue items in UiPath Orchestrator UI
  - [ ] Verify SpecificContent fields match expectations

- [ ] **Task 5.5**: Error scenario testing
  - [ ] Test with unregistered user → verify 400 response, no orphaned records
  - [ ] Test with invalid Entity Store credentials → verify 500 response
  - [ ] Test with invalid UiPath credentials → verify 500 response
  - [ ] Test bulk add failure → verify TenderFiles deleted, Project/Submission remain
  - [ ] Test network timeout scenarios
  - [ ] Verify all errors are logged with sufficient context

- [ ] **Task 5.6**: Performance & load testing
  - [ ] Test submission with 1 file
  - [ ] Test submission with 10 files
  - [ ] Test submission with 50+ files
  - [ ] Measure response times
  - [ ] Check for any memory leaks or resource issues
  - [ ] Verify batch size limits (if any) on UiPath bulk endpoint

### Phase 6: Documentation & Deployment
- [ ] **Task 6.1**: Update environment variable documentation
  - [ ] Update `docs/ENVIRONMENT_VARIABLES.md` with new variables
  - [ ] Document removed `UIPATH_API_URL` variable
  - [ ] Add descriptions for each new variable
  - [ ] Add example values and format requirements

- [ ] **Task 6.2**: Update deployment documentation
  - [ ] Update `docs/DEPLOYMENT.md` with new azd env commands
  - [ ] Document how to obtain UiPath credentials (app_id, api_key, folder_id)
  - [ ] Document how to find/create queue in UiPath Orchestrator
  - [ ] Add troubleshooting section for common issues

- [ ] **Task 6.3**: Update architecture documentation
  - [ ] Update `docs/ARCHITECTURE.md` with Entity Store integration
  - [ ] Document the new data flow diagram
  - [ ] Explain CUID reference linking
  - [ ] Document rollback behavior

- [ ] **Task 6.4**: Create implementation summary document
  - [ ] Document all changes made
  - [ ] Include before/after comparison
  - [ ] List breaking changes (API response structure)
  - [ ] Document migration path for existing deployments

- [ ] **Task 6.5**: Deploy to development environment
  - [ ] Run `azd env set` commands for all new variables
  - [ ] Run `azd deploy` to redeploy with new configuration
  - [ ] Verify container app starts successfully
  - [ ] Check logs for any initialization errors
  - [ ] Test one submission in dev environment

- [ ] **Task 6.6**: Deploy to production environment
  - [ ] Coordinate deployment window
  - [ ] Set production environment variables
  - [ ] Deploy updated infrastructure and app
  - [ ] Verify production deployment successful
  - [ ] Monitor logs for first few submissions
  - [ ] Document any issues and resolutions

## Open Questions

### 1. **CUID Library Selection**
There are multiple Python CUID libraries available (`pycuid`, `cuid2`, `python-cuid`). Which should we use?
- **Option A**: `pycuid2` - Implements CUID2 spec (latest version, more entropy)
- **Option B**: `pycuid` - Original CUID implementation (more mature, wider usage)
- **Decision needed**: Confirm with team which library/version is preferred
- DECISION : use pip install cuid2

### 2. **Queue Item Priority Logic**
Currently, all queue items are set to `"High"` priority. Should this be:
- **Static**: Always "High" for all submissions
- **Dynamic**: Based on tender urgency, file count, or other criteria
- **Configurable**: Environment variable to set default priority
- **Decision needed**: Confirm priority strategy with stakeholders
- DECISION : Keep High

### 3. **Token Caching Strategy**
The UiPath OAuth token is fetched on every `submit_extraction_job()` call. Should we:
- **No caching**: Current approach - simple but potentially rate-limited
- **Instance-level caching**: Cache token in `UiPathClient` instance with expiry check
- **Global caching**: Use Redis/similar for token sharing across requests
- **Decision needed**: Assess UiPath rate limits and determine if caching is necessary
- DECISION : No caching

### 4. **Batch Metadata Blob Updates**
The current system creates batch metadata blobs in Azure Blob Storage. With the new Entity Store tracking, should we:
- **Keep both**: Maintain blob metadata AND Entity Store records (redundant but backward compatible)
- **Remove blobs**: Rely solely on Entity Store for metadata (cleaner, single source of truth)
- **Hybrid**: Store minimal metadata in blobs with reference to Entity Store submission ID
- **Decision needed**: Determine long-term metadata strategy and migration plan
- DECISION : Keep Both