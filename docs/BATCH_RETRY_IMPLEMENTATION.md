# Batch Retry & Resilience Implementation

## Overview

This document describes the complete implementation of automatic retry mechanisms and enhanced failure handling for UiPath batch submissions. The solution addresses timeout issues with large batches and provides resilience against container recycling and unhandled exceptions.

## Problem Statement

### Initial Issue
When submitting extraction batches with a high number of documents (50+ files), the HTTP request would timeout and the frontend would show an error. While the batch continued processing in the backend, the user experience was poor.

### Additional Concerns
- **Container Recycling**: If the container restarts during background processing, the batch submission could be lost
- **Unhandled Exceptions**: Network failures or UiPath API errors during submission could leave batches stuck in 'pending' state
- **Lack of Visibility**: No way to see submission history or troubleshoot failed batches

## Solution Architecture

### Three-Layer Approach

#### 1. Async Job Submission (Immediate Response)
- **Backend**: Modified `POST /api/uipath/extract` endpoint to spawn background thread
- **Threading**: Uses daemon threads to avoid blocking HTTP response
- **Response Time**: Returns HTTP 202 immediately after creating batch metadata
- **User Benefit**: No more timeout errors, smooth frontend experience

#### 2. Automatic Retry Worker (Container Resilience)
- **Background Thread**: Daemon thread running every 5 minutes
- **Detection**: Finds batches in 'pending' status older than 5 minutes
- **Recovery**: Automatically retries UiPath submission
- **Fault Tolerance**: Handles exceptions at tender/batch/retry levels independently
- **Container Safety**: Restarts automatically when container recycles

#### 3. Enhanced Visibility & Manual Control
- **Submission History**: Tracks all submission attempts with timestamps and outcomes
- **Error Tracking**: Stores last error message for debugging
- **UiPath References**: Preserves job IDs for external tracking
- **Manual Retry**: UI button allows users to retry failed batches
- **Audit Trail**: Complete history of all submission attempts

## Implementation Details

### Backend Changes

#### 1. Enhanced Batch Metadata (`backend/services/blob_storage.py`)

Added new metadata fields to track batch lifecycle:

```python
# New fields added to batch metadata
submission_attempts: List[Dict]  # Array of attempt records
last_error: str                  # Most recent error message
uipath_reference: str           # UiPath job reference ID
uipath_submission_id: str       # UiPath submission ID
uipath_project_id: str          # UiPath project ID
```

**New Methods:**
- `update_batch(tender_id, batch_id, updates)`: Generic update method with JSON serialization for lists/dicts
- Enhanced `create_batch()`: Initializes new tracking fields
- Enhanced `get_batch()`: Returns tracking fields with JSON deserialization

#### 2. Async Submission Worker (`backend/app.py`)

**Function**: `_process_uipath_submission_async()`

**Flow:**
1. Get current batch metadata to access submission attempts
2. Record attempt start timestamp with 'in_progress' status
3. Submit job to UiPath API
4. On success:
   - Update attempt status to 'success' with reference
   - Update batch status to 'running'
   - Store UiPath job identifiers
   - Clear last_error field
5. On failure:
   - Update attempt status to 'failed' with error message
   - Update batch status to 'failed'
   - Store error in last_error field

**Error Handling:**
- `ValueError`: User validation errors (email not found)
- `Exception`: UiPath API errors, network failures
- Nested try/except: Prevents update failures from crashing worker

#### 3. Retry Worker (`backend/app.py`)

**Function**: `retry_stuck_batches()`

**Characteristics:**
- Runs as daemon thread (started at app initialization)
- Infinite loop with 5-minute sleep intervals
- Scans all tenders for stuck batches

**Detection Logic:**
```python
if (
    batch_status == 'pending' and
    time_since_submission > 5 minutes
):
    retry_submission()
```

**Fault Isolation:**
- Try/except around tender loop: Failure on one tender doesn't break others
- Try/except around batch loop: Failure on one batch doesn't break others
- Try/except around retry attempt: Retry failure doesn't crash worker

**Startup:**
```python
# Started immediately when app initializes
retry_thread = threading.Thread(target=retry_stuck_batches, daemon=True)
retry_thread.start()
```

#### 4. Manual Retry Endpoint

**Endpoint**: `POST /api/tenders/<tender_id>/batches/<batch_id>/retry`

**Validation:**
- Verifies batch exists (404 if not found)
- Checks batch status in ['pending', 'failed'] (400 otherwise)
- Verifies tender exists (404 if not found)
- Ensures batch has files to process (400 if empty)

**Process:**
1. Retrieve batch details from metadata
2. Extract submission parameters (file_paths, category, etc.)
3. Spawn new background thread with `_process_uipath_submission_async()`
4. Return HTTP 202 with success message
5. Background thread handles actual submission and updates

**Response:**
```json
{
  "success": true,
  "message": "Batch retry initiated. Processing in background."
}
```

### Frontend Changes

#### 1. Type Definitions (`frontend/src/types/index.ts`)

Enhanced `Batch` interface with tracking fields:

```typescript
export interface Batch {
    // ... existing fields ...
    
    // Enhanced tracking fields
    submission_attempts?: Array<{
        timestamp: string;
        status: string;
        reference?: string;
        error?: string;
    }>;
    last_error?: string;
    uipath_reference?: string;
    uipath_submission_id?: string;
    uipath_project_id?: string;
}
```

#### 2. BatchViewer Component (`frontend/src/components/BatchViewer.tsx`)

**New Features:**

1. **Retry Button**
   - Shown when `batch.status === 'failed' || batch.status === 'pending'`
   - Calls `/api/tenders/${tenderId}/batches/${batch.batch_id}/retry`
   - Shows confirmation dialog before retry
   - Disabled during retry operation
   - Returns to batch list on success

2. **Submission History Section**
   - Displays all submission attempts chronologically
   - Shows: attempt number, timestamp, status, reference, error
   - Color-coded by status (green=success, red=failed, blue=in_progress)
   - Truncates long error messages with hover tooltip

3. **Last Error Box**
   - Yellow warning box displaying most recent error
   - Only shown when `batch.last_error` is present
   - Full error message with word-wrap for readability

4. **UiPath Reference Display**
   - Shows UiPath reference ID when available
   - Displayed in header metadata section
   - Monospace font for easy copying

**New Props:**
- `tenderId`: Required for retry endpoint URL construction

#### 3. Component Integration (`frontend/src/pages/TenderManagementPage.tsx`)

**Changes:**
- Pass `tenderId={tenderId!}` prop to BatchViewer component
- Uses existing `tenderId` from `useParams` hook

#### 4. Styling (`frontend/src/components/BatchViewer.css`)

**New Styles:**

1. **Retry Button**
   - Primary blue color (#0d6efd)
   - Disabled state with gray background
   - Hover effect with darker blue

2. **Submission History**
   - Light gray background container
   - White attempt cards with left border color coding
   - Green border for success, red for failed, blue for in-progress

3. **Attempt Items**
   - Flexbox layout with responsive wrapping
   - Fixed widths for attempt number and timestamp
   - Status badges with appropriate colors
   - Error messages with truncation and hover hint

4. **Last Error Box**
   - Yellow background (#fff3cd) with warning border
   - Warning icon in heading
   - Word-break for long error messages

5. **Responsive Design**
   - Mobile-friendly with flex wrapping
   - Full-width timestamps and errors on small screens

## Usage

### Automatic Recovery

The system automatically handles:
- **Large Batch Timeouts**: Background processing with immediate HTTP response
- **Container Restarts**: Retry worker resumes stuck batches after restart
- **Network Failures**: Automatic retry every 5 minutes for failed submissions

### Manual Intervention

When viewing a batch in the UI:

1. **Identify Failed Batch**: Look for red 'failed' status badge
2. **Check Error Details**: Review last error box and submission history
3. **Retry if Needed**: Click "🔄 Retry Submission" button
4. **Confirm Action**: Accept confirmation dialog
5. **Monitor Progress**: Batch status updates automatically

### Monitoring

**Submission History:**
- View complete audit trail of all submission attempts
- Each attempt shows: timestamp, outcome, error (if failed), UiPath reference (if successful)
- Helps identify intermittent vs persistent issues

**Error Investigation:**
- Last error box shows most recent failure reason
- Common errors:
  - "User validation failed": Email not found in UiPath tenant
  - "Connection timeout": Network connectivity issue
  - "401 Unauthorized": UiPath token expired
  - "404 Not Found": UiPath project/folder misconfigured

## Testing Recommendations

### 1. Large Batch Test
- Create batch with 100+ files
- Verify immediate HTTP 202 response
- Confirm background processing completes
- Check submission_attempts array populated

### 2. Container Restart Test
- Submit batch and immediately restart container
- Wait for container to start
- Verify retry worker detects stuck batch within 5 minutes
- Confirm batch completes successfully

### 3. Failure Recovery Test
- Temporarily break UiPath configuration (invalid credentials)
- Submit batch and observe failure
- Fix UiPath configuration
- Click retry button in UI
- Verify batch succeeds on retry

### 4. Error Visibility Test
- Cause intentional failure (invalid email)
- View batch in UI
- Verify last error box displays error message
- Check submission history shows failed attempt
- Confirm error details are helpful for debugging

## Configuration

### Retry Interval

**Location**: `backend/app.py` line ~260

```python
time.sleep(300)  # 5 minutes = 300 seconds
```

**Adjustment**: Change sleep duration to modify retry frequency
- Shorter interval: Faster recovery, higher CPU usage
- Longer interval: Lower overhead, slower recovery

### Stuck Batch Threshold

**Location**: `backend/app.py` line ~290

```python
time_since_submission = datetime.utcnow() - submitted_at
if time_since_submission > timedelta(minutes=5):
    # Retry batch
```

**Adjustment**: Change `minutes=5` to different value
- Recommendation: Keep at 5-10 minutes to avoid retrying batches still processing

### Thread Configuration

Both workers use daemon threads:
```python
daemon=True  # Thread terminates when main process exits
```

**Production Note**: Daemon threads ensure clean shutdown, but may lose in-flight work during container stops. Consider graceful shutdown hooks if needed.

## Performance Considerations

### Thread Count
- **Submission Threads**: One per batch submission (short-lived, typically <30s)
- **Retry Worker**: Single persistent thread running indefinitely
- **Impact**: Minimal CPU/memory overhead with typical workload (<10 concurrent batches)

### Metadata Operations
- **Read Frequency**: Every 5 minutes for retry worker + on-demand for UI
- **Write Frequency**: Once per submission attempt (successful or failed)
- **Blob Storage**: Metadata stored as blob headers, very fast read/write

### Scalability
- **Multiple Instances**: Retry worker in each instance processes independently
- **Race Condition**: Possible duplicate retries if multiple instances detect same stuck batch
- **Mitigation**: UiPath API is idempotent, duplicate submissions generally safe
- **Future Enhancement**: Distributed locking (Redis/CosmosDB) if needed

## Troubleshooting

### Batch Stuck in Pending

**Symptoms**: Batch shows 'pending' status for >10 minutes

**Diagnosis:**
1. Check backend logs for retry worker activity: `azd logs`
2. Look for "Retrying batch" messages
3. Check submission_attempts array in batch metadata

**Possible Causes:**
- Retry worker crashed (check logs for exceptions)
- UiPath API consistently failing (check error messages)
- Network connectivity issues between container and UiPath

**Resolution:**
- Click manual retry button in UI
- Check UiPath service status
- Verify OAuth token not expired

### Retry Button Not Showing

**Symptoms**: Failed batch doesn't show retry button

**Diagnosis:**
1. Check batch status in browser DevTools
2. Verify status is 'failed' or 'pending'
3. Check console for JavaScript errors

**Possible Causes:**
- Batch status is 'running' or 'completed'
- Frontend component not receiving updated batch data
- Browser caching old component version

**Resolution:**
- Refresh page to reload batch data
- Clear browser cache
- Check backend response includes status field

### Submission History Missing

**Symptoms**: No attempts shown in UI

**Diagnosis:**
1. Check batch metadata in Azure Portal
2. Look for `submission_attempts` property
3. Verify it's valid JSON array

**Possible Causes:**
- Batch created before enhancement (no tracking fields)
- Metadata update failed during submission
- JSON serialization error

**Resolution:**
- Manually retry batch to populate attempts
- Check backend logs for serialization errors
- Verify blob_service.update_batch() succeeds

## Future Enhancements

### Potential Improvements

1. **Exponential Backoff**: Increase retry interval after multiple failures
2. **Max Retry Limit**: Stop retrying after X failed attempts
3. **Notification System**: Email/Teams notification on persistent failures
4. **Dashboard Metrics**: Track success/failure rates, average retry count
5. **Distributed Locking**: Prevent duplicate retries across instances
6. **Priority Queue**: Retry older batches first
7. **Batch Pause/Resume**: Allow users to temporarily pause retries
8. **Webhook Integration**: UiPath callback for completion status

### Migration Path

For batches created before this enhancement:
- No action needed - will work normally
- Tracking fields initialize on first retry
- Historical batches won't have submission history

## References

- **Implementation Date**: 2024 (based on conversation)
- **Related Docs**: 
  - `BATCH_SUBMISSION_IMPLEMENTATION.md` - Original batch submission
  - `UIPATH_CONFIGURATION_GUIDE.md` - UiPath setup
  - `CONTAINER_APP_ENV_VARS.md` - Environment configuration
- **Pull Request**: (Add PR number when merged)
- **Testing Checklist**: See "Testing Recommendations" section above
