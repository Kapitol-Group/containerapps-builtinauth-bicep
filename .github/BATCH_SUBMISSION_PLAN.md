---
title: Batch Submission and File Categorization System
version: 1.0
date_created: 2025-10-29
last_updated: 2025-10-29
---
# Implementation Plan: Batch Submission and File Categorization System

This feature enhances the tender workflow by introducing a batch submission system that automatically categorizes files based on selected discipline and moves submitted files to a separate view, keeping the main file browser clean for ongoing work.

## Architecture and Design

### High-Level Architecture

The system will introduce a **batch-based workflow** with the following key components:

1. **Batch Data Model**: New persistent storage for extraction batches in Azure Blob Storage
2. **Automatic Categorization**: Immediate file metadata updates when extraction is queued
3. **Dual-View File Browser**: Tabbed interface separating active files from submitted batches
4. **Backend Batch Management**: New API endpoints and storage service methods

### Data Model

#### Batch Metadata Structure
Batches will be stored as metadata blobs in blob storage:
- **Path**: `{tender-id}/.batch_{batch-id}`
- **Metadata Fields**:
  - `batch_id`: Unique identifier (UUID or timestamp-based)
  - `batch_name`: User-friendly name (e.g., "Structural Batch 1")
  - `job_id`: UiPath extraction job identifier
  - `discipline`: Selected discipline (Architectural, Structural, etc.)
  - `file_paths`: JSON array of file paths included in the batch
  - `title_block_coords`: JSON object with coordinates
  - `status`: Extraction status (pending, running, completed, failed)
  - `submitted_at`: ISO timestamp
  - `submitted_by`: User who submitted the batch
  - `file_count`: Number of files in the batch

#### File Metadata Updates
When files are submitted for extraction, their blob metadata will be updated:
- `category`: Changed from "uncategorized" to the selected discipline
- `batch_id`: Reference to the batch they belong to
- `submitted_at`: Timestamp when added to batch

### Frontend Architecture Changes

#### Component Structure
```
TenderManagementPage
├── FileUploadZone (unchanged)
├── SharePointFileBrowser (unchanged)
├── FileBrowserTabs (NEW)
│   ├── Tab: "Active Files"
│   │   └── FileBrowser (filtered: not in batch)
│   └── Tab: "Submitted Batches"
│       └── BatchList (NEW)
│           └── BatchViewer (NEW - shows files in batch, read-only)
├── FilePreview (unchanged)
└── ExtractionModal (modified - creates batch on submit)
```

#### State Management
New state variables in `TenderManagementPage`:
- `activeTab`: 'files' | 'batches'
- `batches`: Array of batch metadata objects
- `selectedBatch`: Currently selected batch for viewing
- `activeFil es`: Filtered list excluding files in batches
- `batchFiles`: Files belonging to currently selected batch

### Backend Architecture Changes

#### New API Endpoints
1. **POST /api/tenders/{tender_id}/batches** - Create a new batch
2. **GET /api/tenders/{tender_id}/batches** - List all batches for a tender
3. **GET /api/tenders/{tender_id}/batches/{batch_id}** - Get batch details and files
4. **PATCH /api/tenders/{tender_id}/batches/{batch_id}** - Update batch status
5. **DELETE /api/tenders/{tender_id}/batches/{batch_id}** - Delete a batch (admin only)

#### Modified API Endpoints
- **GET /api/tenders/{tender_id}/files** - Add optional query param `?exclude_batched=true`
- **POST /api/uipath/extract** - Modified to create batch and update file metadata

#### BlobStorageService New Methods
- `create_batch()`: Create batch metadata blob
- `list_batches()`: List all batches for a tender
- `get_batch()`: Get batch details by ID
- `update_batch_status()`: Update batch status
- `delete_batch()`: Delete batch metadata
- `get_batch_files()`: Get all files belonging to a batch
- `update_files_category()`: Bulk update category for multiple files
- `add_files_to_batch()`: Update file metadata to reference batch

### Data Flow

#### Extraction Queue Flow
1. User selects files in "Active Files" tab
2. User clicks "Queue Extraction"
3. ExtractionModal opens:
   - Shows selected files
   - User selects discipline
   - User defines title block region
4. User submits:
   - **Backend creates batch** (POST /api/tenders/{tender_id}/batches)
   - **Backend updates file metadata** with new category and batch_id
   - **Backend queues UiPath job** with batch_id reference
   - **Backend returns batch details**
5. Frontend:
   - Reloads files and batches
   - Switches to "Batches" tab
   - Submitted files disappear from "Active Files"
   - New batch appears in "Batches" list

#### Batch Viewing Flow
1. User switches to "Batches" tab
2. System loads batch list (GET /api/tenders/{tender_id}/batches)
3. User clicks on a batch
4. System loads batch files (GET /api/tenders/{tender_id}/batches/{batch_id})
5. BatchViewer displays:
   - Batch metadata (discipline, submitted by, date, status)
   - Read-only file list (no selection checkboxes)
   - Preview still works for individual files
   - Status indicator (future: can show UiPath job progress)

## Tasks

### Backend Tasks

#### 1. Blob Storage Service - Batch Management
- [ ] Add `create_batch()` method to create batch metadata blob
  - Generate unique batch_id (UUID v4)
  - Store batch metadata in `{tender-id}/.batch_{batch-id}`
  - Return batch object with all metadata
- [ ] Add `list_batches()` method to list all batches
  - Filter blobs by `.batch_*` prefix under tender folder
  - Parse metadata and return array of batch objects
  - Sort by `submitted_at` descending
- [ ] Add `get_batch()` method to retrieve single batch
  - Load batch metadata blob
  - Return batch object or None if not found
- [ ] Add `update_batch_status()` method
  - Update batch metadata blob with new status
  - Track status transitions (pending → running → completed/failed)
- [ ] Add `get_batch_files()` method
  - Query files with matching `batch_id` in metadata
  - Return array of file objects
- [ ] Add `update_files_category()` bulk update method
  - Accept list of file paths and new category
  - Update blob metadata for each file
  - Add batch_id to file metadata
- [ ] Modify `list_files()` to support `exclude_batched` parameter
  - Filter out files with `batch_id` metadata when parameter is True

#### 2. API Routes - Batch Endpoints
- [ ] Implement POST `/api/tenders/{tender_id}/batches`
  - Accept: file_paths, discipline, title_block_coords
  - Validate all required fields
  - Create batch using `create_batch()`
  - Update file categories using `update_files_category()`
  - Return batch object with 201 status
- [ ] Implement GET `/api/tenders/{tender_id}/batches`
  - Call `list_batches()`
  - Return array of batch objects
  - Handle empty list gracefully
- [ ] Implement GET `/api/tenders/{tender_id}/batches/{batch_id}`
  - Call `get_batch()` for metadata
  - Call `get_batch_files()` for file list
  - Return combined object with batch + files
  - Return 404 if batch not found
- [ ] Implement PATCH `/api/tenders/{tender_id}/batches/{batch_id}`
  - Accept status updates
  - Validate status values (pending, running, completed, failed)
  - Call `update_batch_status()`
  - Return updated batch object
- [ ] Modify GET `/api/tenders/{tender_id}/files`
  - Add `exclude_batched` query parameter support
  - Pass parameter to `list_files()`
- [ ] Modify POST `/api/uipath/extract`
  - Create batch FIRST before calling UiPath
  - Pass batch_id to UiPath job metadata
  - Update file categories immediately
  - Return batch_id in response along with job_id
  - Handle rollback if UiPath submission fails

#### 3. Error Handling and Validation
- [ ] Add validation for batch creation
  - Ensure files exist before creating batch
  - Validate discipline is in allowed list
  - Validate title_block_coords structure
- [ ] Add error handling for batch operations
  - Handle blob storage errors gracefully
  - Return appropriate HTTP status codes
  - Provide meaningful error messages
- [ ] Add logging for batch lifecycle events
  - Log batch creation
  - Log status transitions
  - Log errors with context

### Frontend Tasks

#### 4. Type Definitions
- [ ] Add `Batch` interface to `types/index.ts`
  - Define all batch metadata fields
  - Match backend data structure
- [ ] Add `BatchFile` type (extends TenderFile with batch info)
- [ ] Update `ExtractionJob` interface to include `batch_id`

#### 5. API Service Layer
- [ ] Add `batchesApi` object to `services/api.ts`
  - `create()`: POST batch creation
  - `list()`: GET all batches for tender
  - `get()`: GET single batch with files
  - `updateStatus()`: PATCH batch status
- [ ] Modify `filesApi.list()` to accept `excludeBatched` parameter
- [ ] Update `uipathApi.queueExtraction()` return type to include batch_id

#### 6. New Components

##### BatchList Component
- [ ] Create `components/BatchList.tsx`
  - Display list of batches in card/list format
  - Show: discipline, file count, submitted date, submitted by, status
  - Handle click to select batch for viewing
  - Show loading state while fetching
  - Show empty state when no batches
  - Apply status-based styling (pending=yellow, running=blue, completed=green, failed=red)
- [ ] Create `components/BatchList.css`
  - Style batch cards with clear visual hierarchy
  - Add status indicator badges
  - Responsive layout

##### BatchViewer Component
- [ ] Create `components/BatchViewer.tsx`
  - Display batch metadata header (discipline, date, user, status)
  - Show file list (reuse FileBrowser styling but read-only)
  - Remove checkboxes and delete buttons
  - Keep file preview capability
  - Add "Close" button to return to batch list
  - Show title block coordinates info (display only)
- [ ] Create `components/BatchViewer.css`
  - Style metadata header with info cards
  - Style read-only file list
  - Add visual indicator that files are not editable

##### FileBrowserTabs Component
- [ ] Create `components/FileBrowserTabs.tsx`
  - Tab switching UI ("Active Files" | "Submitted Batches")
  - Manage active tab state
  - Pass filtered data to child components
  - Handle badge counts (files count, batches count)
- [ ] Create `components/FileBrowserTabs.css`
  - Style tab navigation
  - Active tab highlighting
  - Badge styling for counts

#### 7. Component Modifications

##### TenderManagementPage
- [ ] Add state management
  - `activeTab`: 'files' | 'batches'
  - `batches`: Batch[]
  - `selectedBatch`: Batch | null
  - `activeFil es`: TenderFile[] (filtered)
  - `batchFiles`: TenderFile[] (for selected batch)
- [ ] Add `loadBatches()` function
  - Fetch batches from API
  - Update batches state
  - Handle errors
- [ ] Modify `loadFiles()` function
  - Add `excludeBatched=true` parameter when on "Active Files" tab
  - Filter logic based on active tab
- [ ] Add `handleBatchSelect()` function
  - Fetch batch details and files
  - Update selectedBatch and batchFiles state
- [ ] Modify extraction success handler
  - Reload both files and batches
  - Switch to "Batches" tab automatically
  - Clear file selection
- [ ] Replace FileBrowser with FileBrowserTabs component
  - Pass activeTab and setActiveTab
  - Pass filtered files for active tab
  - Pass batches for batches tab
  - Handle tab switching logic
- [ ] Add useEffect for batch loading
  - Load batches when component mounts
  - Reload when tender changes

##### ExtractionModal
- [ ] Modify `handleSubmit()` function
  - Call new batch creation API instead of direct UiPath call
  - Backend handles both batch creation and UiPath submission
  - Receive batch_id in response
  - Pass batch_id to parent's onSubmit callback
- [ ] Update success message
  - "Batch submitted successfully!" instead of "Extraction job queued"
  - Mention that files have been categorized
- [ ] Add error handling for batch creation failures

##### FileBrowser
- [ ] Add `readOnly` prop (boolean, default false)
  - When true, hide checkboxes
  - When true, hide delete buttons
  - When true, disable multi-selection
  - Still allow single-click for preview
- [ ] Add visual indicator for read-only mode
  - Gray out header or add "(Read-Only)" text
  - Change cursor style

#### 8. Styling and UX
- [ ] Update `TenderManagementPage.css`
  - Add styles for tab container
  - Adjust layout for dual-view
- [ ] Add status badge styles
  - Color coding for batch statuses
  - Icons for different states (optional)
- [ ] Add empty state illustrations
  - "No active files" in Files tab
  - "No batches submitted yet" in Batches tab
- [ ] Add loading skeletons
  - For batch list while loading
  - For batch files while loading
- [ ] Ensure responsive design
  - Tabs work on mobile
  - Batch cards stack properly

#### 9. Testing and Polish
- [ ] Test complete flow
  - Upload files
  - Select files and queue extraction
  - Verify files disappear from Active Files
  - Verify batch appears in Batches tab
  - Verify automatic tab switch
  - Verify batch can be viewed
  - Verify files are read-only in batch
  - Verify file preview still works
- [ ] Test edge cases
  - Empty batches (should not happen, but handle gracefully)
  - Batch with single file
  - Multiple batches
  - Switching between batches
  - Deleting files that are in batches (should be prevented)
- [ ] Test error scenarios
  - Batch creation failure
  - Network errors
  - Invalid data
- [ ] Add loading states throughout
- [ ] Add appropriate error messages
- [ ] Verify all file categories update correctly

### Documentation Tasks

#### 10. Documentation Updates
- [ ] Update `docs/ARCHITECTURE.md`
  - Document batch system architecture
  - Update data flow diagrams
- [ ] Update `docs/IMPLEMENTATION_SUMMARY.md`
  - Add batch management section
- [ ] Update `README.md` or quickstart guides
  - Document new batch workflow for end users
  - Add screenshots of tabbed interface (after implementation)
- [ ] Add inline code comments
  - Document batch metadata structure
  - Explain filtering logic
  - Comment complex state management

## Open Questions

### 1. Batch Deletion and File Recovery
**Question**: If a batch is deleted (admin feature), what should happen to the files?
- **Option A**: Files remain categorized but lose batch_id reference (orphaned, can be re-batched)
- **Option B**: Files revert to "uncategorized" status and batch_id is removed
- **Option C**: Files are deleted along with the batch (destructive)

**Recommendation**: Option A - preserve the categorization work but allow files to be re-batched if needed. This is least destructive and maintains data integrity.

### 2. Duplicate File Handling
**Question**: What if a user tries to upload a file that's already in a submitted batch?
- **Option A**: Allow duplicates with different paths (current behavior)
- **Option B**: Prevent uploads of files with same name if already in batch
- **Option C**: Show warning but allow override

**Recommendation**: Option A for now (keep current behavior), but add a future enhancement to detect and warn about duplicates.

### 3. Status Update Mechanism
**Question**: How should batch status be updated from UiPath job status?
- **Option A**: Frontend polls UiPath job status and updates batch status via PATCH endpoint
- **Option B**: Backend webhook from UiPath updates batch status automatically
- **Option C**: Manual status updates only (for MVP)

**Recommendation**: Option C for initial implementation (manual/mock), with Option B as a future enhancement when UiPath integration is fully configured. The infrastructure is in place to support automated status updates later.

