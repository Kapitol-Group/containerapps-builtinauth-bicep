# Graph API Path Lookup Integration

## Overview

Since the SharePoint FilePicker doesn't expose the folder path directly in the pick command response, we now use Microsoft Graph API to query the path dynamically.

## How It Works

### 1. Extract Basic Identifiers from FilePicker
From the pick command, we extract:
- **Item ID**: `item.id` (e.g., `"01U7IOQIITHT4P62EPRVFKSGOPLYDDBCHR"`)
- **Drive ID**: `item.parentReference.driveId` (the library ID)
- **Site ID**: Constructed from `item.sharepointIds.siteId` and `webId`

### 2. Query Graph API for Path
We make a Graph API call to get the item details:

```
GET https://graph.microsoft.com/v1.0/drives/{driveId}/items/{itemId}
Authorization: Bearer {accessToken}
```

### 3. Extract Path from Response
The Graph API response includes:
```json
{
  "id": "01U7IOQIITHT4P62EPRVFKSGOPLYDDBCHR",
  "name": "002 Kapitol Doc Control",
  "parentReference": {
    "driveId": "b!0jwoP7JSq0-1T7BO1VzgF0gDv3qd4bxAie_thIt_Lx8oDMee3BdeQL_TE8L5eoVD",
    "path": "/drive/root:/01 TENDERS/Active/453 - M2S6 RETROFIT/1.0 DOCUMENTS"
  },
  "folder": { ... }
}
```

We extract and clean the path:
- Remove `/drive/root:` prefix
- Append item name if it's a folder
- Result: `/01 TENDERS/Active/453 - M2S6 RETROFIT/1.0 DOCUMENTS/002 Kapitol Doc Control`

## Implementation

### New Functions in `sharepoint.ts`

#### `fetchItemPathFromGraph(driveId, itemId, accessToken)`
- Queries Graph API for item details
- Extracts path from `parentReference.path`
- Cleans and formats the path
- Returns the full folder path

#### `extractSharePointIdentifiersWithPath(pickData, accessToken?)`
- Enhanced version of `extractSharePointIdentifiers()`
- First tries to get path from pick data
- If unavailable, uses Graph API to fetch it
- Returns identifiers with `pathSource` indicator:
  - `'pickData'`: Path was in FilePicker response
  - `'graphApi'`: Path was fetched via Graph API
  - `'unavailable'`: Could not determine path

### Updated CreateTenderModal

The handler functions now:
1. Get a Graph API access token
2. Call `extractSharePointIdentifiersWithPath()` with the token
3. Display the path with a label showing the source

```typescript
const handleSharePointPathPicked = async (data: any) => {
  // Get Graph API token
  const accessToken = await getDelegatedToken(msalInstance, 'https://graph.microsoft.com');
  
  // Extract identifiers with Graph API fallback
  const identifiers = await extractSharePointIdentifiersWithPath(data, accessToken);
  
  if (identifiers) {
    console.log('Path source:', identifiers.pathSource);
    // Use the identifiers...
  }
};
```

## Token Requirements

The Graph API call requires an access token with:
- **Resource**: `https://graph.microsoft.com`
- **Scopes**: `Files.Read.All`, `Sites.Read.All` (already configured in MSAL)

The same delegated permissions used for SharePoint FilePicker work for Graph API.

### Authentication Flow

The `getDelegatedToken` function now handles multiple scenarios:

1. **Active account exists**: Uses it directly
2. **Cached accounts exist**: Sets the first one as active
3. **No accounts**: Triggers interactive login popup
4. **Token acquisition**: Tries silent first, falls back to popup if needed

This ensures the Graph API call always has a valid token, even if the user hasn't explicitly logged in yet.

## Benefits

1. **Always get the path**: Even when FilePicker doesn't include it
2. **Transparent fallback**: Works with or without FilePicker path data
3. **Clear indication**: Shows where the path came from (pick data vs Graph API)
4. **No user intervention**: Happens automatically in the background

## Testing

When you test the SharePoint folder selection, check the console for:

```
SharePoint path picked - FULL DATA: { ... }
Got Graph API token for path lookup
Fetching item path from Graph API: https://graph.microsoft.com/v1.0/...
Graph API response: { ... }
Extracted path from Graph API: /01 TENDERS/Active/...
Path source: graphApi
```

The UI will show the path with a label:
```
/01 TENDERS/Active/453 - M2S6 RETROFIT/... (via Graph API)
```

## Error Handling

If Graph API fails:
- Falls back to empty path
- Logs warning in console
- UI shows "Selected (path unavailable)"
- Still saves site ID and library ID (which can be used for future lookups)

## Graph API Response Structure

Example response for a folder item:

```json
{
  "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#drives('...')/items/$entity",
  "id": "01U7IOQIITHT4P62EPRVFKSGOPLYDDBCHR",
  "name": "002 Kapitol Doc Control",
  "createdDateTime": "2024-10-15T10:30:00Z",
  "lastModifiedDateTime": "2024-10-20T14:22:00Z",
  "size": 0,
  "webUrl": "https://kapitolgroupcomau.sharepoint.com/sites/...",
  "parentReference": {
    "driveId": "b!0jwoP7JSq0-1T7BO1VzgF0gDv3qd4bxAie_thIt_Lx8oDMee3BdeQL_TE8L5eoVD",
    "driveType": "documentLibrary",
    "id": "01U7IOQIITHT4P62EPRVFKSGOAAAAAAAA",
    "path": "/drive/root:/01 TENDERS/Active/453 - M2S6 RETROFIT/1.0 DOCUMENTS"
  },
  "folder": {
    "childCount": 42,
    "view": {
      "viewType": "thumbnails",
      "sortBy": "name",
      "sortOrder": "ascending"
    }
  },
  "fileSystemInfo": {
    "createdDateTime": "2024-10-15T10:30:00Z",
    "lastModifiedDateTime": "2024-10-20T14:22:00Z"
  }
}
```

Key fields used:
- `parentReference.path`: Parent folder path (format: `/drive/root:/actual/path`)
- `name`: Item name (folder name)
- `folder`: Indicates this is a folder (vs file)
