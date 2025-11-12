# Backend-Driven SharePoint Import Implementation

## Overview

The SharePoint file import functionality has been refactored to use a **backend-driven architecture** instead of the previous browser-based download-and-upload approach. This eliminates browser memory constraints, removes redundant network transfers, and enables proper background processing with progress tracking.

## Key Changes

### 1. Backend API Changes (`backend/app.py`)

#### New Endpoints

**`POST /api/sharepoint/import-files`**
- Accepts tender ID, Graph API access token, and array of file items
- Creates background job for processing imports
- Returns job ID for status polling
- Supports folder structure preservation via `relativePath` field

**`GET /api/sharepoint/import-jobs/<job_id>`**
- Returns real-time status of import job
- Includes: progress, current file, success/error counts, detailed error messages
- Job status: `running`, `completed`, `completed_with_errors`, `failed`

#### Job Tracking
- In-memory job storage with thread-safe access (`import_jobs_lock`)
- Automatic cleanup after 1 hour (configurable via `JOB_CLEANUP_SECONDS`)
- Background threading for non-blocking imports
- Detailed error tracking per file

#### Import Process
```python
# Backend directly downloads from SharePoint
response = requests.get(
    download_url,
    headers={'Authorization': f'Bearer {access_token}'},
    timeout=300
)

# Then uploads to blob storage
blob_service.upload_file(
    tender_id=tender_id,
    file_content=response.content,
    file_name=file_name,
    category=category,
    blob_path=blob_path
)
```

### 2. Frontend Changes

#### SharePoint Utilities (`frontend/src/utils/sharepoint.ts`)

**New Function: `fetchFolderContentsRecursive()`**
- Recursively traverses SharePoint folders using Graph API
- Fetches all files with relative paths preserved
- Handles pagination (Graph API returns max 200 items per request)
- Returns flat array of file metadata ready for backend import

**Recursive Algorithm:**
```typescript
1. Fetch children of current folder (/children endpoint)
2. For each item:
   - If folder: recurse with updated relativePath
   - If file: add to results array with metadata
3. Handle pagination via @odata.nextLink
4. Return aggregated file list
```

#### SharePoint Browser Component (`frontend/src/components/SharePointFileBrowser.tsx`)

**Two-Phase Process:**

**Phase 1: Scanning**
- User selects files/folders from SharePoint picker
- Frontend detects folders vs files
- For folders: calls `fetchFolderContentsRecursive()` to build file list
- Shows "Scanning SharePoint folders..." UI
- Aggregates all files into single array

**Phase 2: Importing**
- Sends complete file list + access token to backend
- Backend returns job ID
- Frontend polls `/api/sharepoint/import-jobs/{job_id}` every 1.5 seconds
- Displays progress: "15 of 47 files: drawing-A-101.pdf"
- Stops polling when status is `completed`, `completed_with_errors`, or `failed`

**State Management:**
```typescript
const [isScanning, setIsScanning] = useState(false);  // Phase 1
const [isImporting, setIsImporting] = useState(false); // Phase 2
const [importProgress, setImportProgress] = useState<{
  current: number;
  total: number;
  currentFile: string;
  status: string;
} | null>(null);
```

#### API Service (`frontend/src/services/api.ts`)

**New Methods:**
```typescript
sharepointApi.importFiles(tenderId, accessToken, items, category)
sharepointApi.getImportJobStatus(jobId)
```

## Benefits of New Architecture

### 1. **No Browser Memory Limits**
- Old: Downloaded entire files to browser memory, then uploaded
- New: Backend streams directly from SharePoint to Blob Storage
- Enables importing 100+ files or large multi-GB folders

### 2. **Network Efficiency**
- Old: SharePoint → Browser (download) → Backend (upload) = 2x transfer
- New: SharePoint → Backend = 1x transfer
- Saves bandwidth and time, especially for large files

### 3. **Background Processing**
- Old: Browser tab had to stay open during entire import
- New: Backend processes in background thread
- User can close tab/navigate away while import continues

### 4. **Better Error Handling**
- Old: Single failure could stop entire import
- New: Continues processing remaining files, reports partial success
- Detailed per-file error messages in job status

### 5. **Progress Visibility**
- Real-time progress updates via polling
- Shows current file being processed
- Displays success/error counts
- Status summary on completion

### 6. **Folder Support**
- Automatically detects folders in SharePoint picker
- Recursively scans all subfolders
- Preserves folder structure in blob storage paths
- No manual file selection needed for large folder trees

## Technical Details

### Token Handling
- Frontend acquires Graph API token via MSAL
- Token sent to backend with each import request
- Backend uses token for SharePoint downloads
- **Note**: Tokens expire in ~1 hour - for very large imports spanning >1 hour, consider implementing token refresh mechanism

### Folder Structure Preservation
```
SharePoint:
  /Drawings/
    Architectural/
      A-101.pdf
      A-102.pdf
    Structural/
      S-201.pdf

Blob Storage:
  {tender-id}/
    Architectural/
      A-101.pdf
      A-102.pdf
    Structural/
      S-201.pdf
```

The `relativePath` field in import items determines blob storage folder structure.

### Concurrency & Resource Management
- Each import job runs in separate daemon thread
- Thread-safe job tracking with locks
- 5-minute timeout per file download
- Pagination handled for folders with 200+ items

### Error Recovery
- **Partial failures**: Continue importing remaining files
- **Network errors**: Logged with file name for retry
- **Job failures**: Status set to `failed`, errors array populated
- **Frontend polling errors**: Shows "Lost connection" message, import continues in background

## Usage Example

### User Workflow
1. Click "Browse SharePoint"
2. Navigate to folder in SharePoint picker
3. Select folder or multiple files
4. Click "Select"
5. Frontend shows "Scanning SharePoint folders..."
6. Frontend shows "Importing files from SharePoint... 15 of 47"
7. On completion: "Successfully imported 47 files" or error summary

### Developer Testing
```bash
# Backend logs show progress
INFO - Started SharePoint import job abc-123 for tender tender-1 with 47 items
INFO - Downloading drawing-A-101.pdf from SharePoint (job abc-123)...
INFO - Uploading drawing-A-101.pdf to blob storage at Architectural/drawing-A-101.pdf...
INFO - Successfully imported drawing-A-101.pdf (job abc-123)
...
INFO - SharePoint import job abc-123 completed: 45 succeeded, 2 failed
```

## Future Enhancements

### 1. Token Refresh for Long Imports
For imports >1 hour, implement:
```typescript
// Frontend periodically refreshes token and updates backend
PATCH /api/sharepoint/import-jobs/{job_id}/token
{ "access_token": "<new_token>" }
```

### 2. Job Persistence
Current: In-memory storage (lost on server restart)
Future: Store in Cosmos DB or blob storage for:
- Crash recovery
- Audit trail
- Multi-server deployments

### 3. Rate Limiting
Prevent resource exhaustion:
- Max 3 concurrent import jobs per user
- Queue system for additional requests
- Configurable worker thread pool

### 4. Resumable Imports
For failed jobs:
```typescript
POST /api/sharepoint/import-jobs/{job_id}/retry
// Re-attempts only failed files
```

### 5. Duplicate Detection
Check blob storage before importing:
- Skip files that already exist (by name + size)
- Or add versioning/overwrite options

## Migration Notes

### Breaking Changes
- Frontend `SharePointFileBrowser` component API unchanged (no breaking changes)
- Backend adds new endpoints (backward compatible)
- Old browser-based import flow completely replaced

### Deployment
1. Deploy backend changes first (new endpoints)
2. Deploy frontend changes second (uses new endpoints)
3. No database migrations required (in-memory storage)
4. No environment variable changes needed

## Testing Checklist

- [ ] Single file import
- [ ] Multiple files import (10+)
- [ ] Single folder import (small, <10 files)
- [ ] Nested folder import (multiple levels deep)
- [ ] Large folder import (100+ files)
- [ ] Mixed selection (files + folders)
- [ ] Error handling (invalid token)
- [ ] Error handling (file download failure)
- [ ] Progress polling (verify real-time updates)
- [ ] Job cleanup (verify cleanup after 1 hour)
- [ ] Folder structure preservation in blob storage
- [ ] Concurrent imports (multiple users)

## Support & Troubleshooting

### Import Not Starting
- Check browser console for token acquisition errors
- Verify Graph API permissions: `Files.Read.All`, `Sites.Read.All`
- Check backend logs for job creation

### Import Stuck at "Scanning"
- Large folder with many files (may take 30+ seconds)
- Graph API rate limiting (backend logs will show 429 errors)
- Network connectivity issues

### Import Fails Immediately
- Check backend logs for detailed error
- Verify tender exists
- Verify access token is valid
- Check blob storage connection

### Partial Import Success
- Check job status errors array for per-file failures
- Common causes: File locked, network timeout, insufficient permissions
- Failed files can be manually re-imported

