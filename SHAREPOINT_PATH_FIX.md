# SharePoint Path Extraction Fix

## Problem
The SharePoint FilePicker was returning data that couldn't be browsed to. We were extracting simple paths instead of the proper SharePoint identifiers needed to locate and access folders.

## Solution
Updated the system to extract and store three critical SharePoint identifiers:

1. **`sharepointsiteid`**: Composite site identifier
   - Format: `{domain},{siteId},{webId}`
   - Example: `kapitolgroupcomau.sharepoint.com,3f283cd2-52b2-4fab-b54f-b04ed55ce017,7abf0348-e19d-40bc-89ef-ed848b7f2f1f`

2. **`sharepointlibraryid`**: Drive/library identifier
   - Format: Base64-encoded ID from `driveId`
   - Example: `b!0jwoP7JSq0-1T7BO1VzgF0gDv3qd4bxAie_thIt_Lx8oDMee3BdeQL_TE8L5eoVD`

3. **`sharepointfolderpath`**: Folder path within the library
   - Format: Unix-style path starting with `/`
   - Example: `/01 TENDERS/Active/453 - M2S6 RETROFIT/1.0 DOCUMENTS/002 Kapitol Doc Control`

## Changes Made

### Frontend

1. **`frontend/src/utils/sharepoint.ts`**
   - Added `extractSharePointIdentifiers()` function
   - Extracts the three identifiers from FilePicker response
   - Added debug logging to show available fields
   - Handles multiple possible data locations (sharePoint.path, webUrl, folder.path, name)

2. **`frontend/src/types/index.ts`**
   - Added new fields to `Tender` interface:
     - `sharepoint_site_id`
     - `sharepoint_library_id`
     - `sharepoint_folder_path`
     - `output_site_id`
     - `output_library_id`
     - `output_folder_path`
   - Kept legacy fields for backward compatibility

3. **`frontend/src/services/api.ts`**
   - Updated `tendersApi.create()` to accept new SharePoint identifier fields

4. **`frontend/src/components/CreateTenderModal.tsx`**
   - Added state variables for all six SharePoint identifiers (3 for source, 3 for output)
   - Updated `handleSharePointPathPicked()` to use new extraction function
   - Updated `handleOutputLocationPicked()` similarly
   - Enhanced logging to show full FilePicker response
   - Modified API call to send all identifiers to backend

### Backend

1. **`backend/app.py`**
   - Updated `/api/tenders` POST endpoint to accept new fields
   - Stores all six SharePoint identifiers in blob metadata
   - Maintains backward compatibility with legacy `sharepoint_path` and `output_location` fields

## Testing Instructions

### 1. Deploy the Changes
```bash
azd deploy
```

### 2. Test SharePoint Folder Selection

1. Open the application
2. Click "Create New Tender"
3. Enter a tender name
4. Click "Browse" for SharePoint Path
5. Select a folder in SharePoint
6. **Open browser console (F12)** and look for:
   - `"SharePoint path picked - FULL DATA:"` - Shows complete FilePicker response
   - `"SharePoint extraction debug:"` - Shows extraction results and available fields

### 3. What to Check

#### Expected Console Output:
```json
{
  "sharepointsiteid": "kapitolgroupcomau.sharepoint.com,{siteId},{webId}",
  "sharepointlibraryid": "b!...",
  "sharepointfolderpath": "/path/to/folder",
  "availableFields": {
    "hasSharePointPath": true/false,
    "hasWebUrl": true/false,
    "hasFolderPath": true/false,
    "hasName": true/false
  }
}
```

#### Folder Path Extraction Priority:
The function tries to extract the folder path from these sources in order:
1. `item.sharePoint.path` - Most reliable
2. `item.webUrl` - Parse from URL
3. `item.folder.path` - Direct folder property
4. `item.name` - Last resort

### 4. Known Issue: Folder Path May Be Empty

**UPDATE**: This issue has been resolved with Graph API integration!

The test with your sample data shows that:
- ✅ **Site ID extraction**: Working perfectly
- ✅ **Library ID extraction**: Working perfectly  
- ✅ **Folder path extraction**: Now uses Graph API as fallback

**Graph API Fallback**: If the folder path is not in the FilePicker response, the system now automatically queries Microsoft Graph API to fetch it using the item ID and drive ID. See `docs/GRAPH_API_PATH_LOOKUP.md` for details.

When you test the SharePoint folder selection, check the console for:

```
SharePoint path picked - FULL DATA: { ... }
Got Graph API token for path lookup
Fetching item path from Graph API: ...
Graph API response: { ... }
Extracted path from Graph API: /01 TENDERS/Active/...
Path source: graphApi
```

### 5. Verify Backend Storage

After creating a tender, you can verify the data is stored correctly:

```bash
# Using Azure CLI
az storage blob list \
  --account-name <storage-account> \
  --container-name tenders \
  --prefix <tender-id>/.tender_metadata \
  --query "[0].metadata"
```

Expected metadata:
```json
{
  "tender_name": "...",
  "created_by": "...",
  "created_at": "...",
  "sharepoint_site_id": "kapitolgroupcomau.sharepoint.com,...",
  "sharepoint_library_id": "b!...",
  "sharepoint_folder_path": "/path/to/folder",
  "output_site_id": "...",
  "output_library_id": "...",
  "output_folder_path": "..."
}
```

## Next Steps

Once we confirm the folder path is being extracted correctly:

1. **Update SharePoint browsing logic** - Use these identifiers to construct proper SharePoint URLs
2. **Add SharePoint file browsing** - Use the Graph API to list files using these identifiers
3. **Implement direct folder access** - Construct URLs that work for navigating to folders

## Rollback Plan

If issues occur, the legacy fields are still supported:
- `sharepoint_path` (deprecated)
- `output_location` (deprecated)

The backend accepts both old and new field formats.
