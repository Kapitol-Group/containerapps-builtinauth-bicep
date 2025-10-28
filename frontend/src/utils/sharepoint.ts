/**
 * SharePoint utility functions for file operations
 */

/**
 * Download a file from SharePoint using a download URL
 * @param downloadUrl The @microsoft.graph.downloadUrl from the FilePicker response
 * @param filename The original filename
 * @param accessToken Optional access token (may not be needed for download URLs)
 * @returns A File object ready for upload
 */
export async function downloadFileFromSharePoint(
    downloadUrl: string,
    filename: string,
    accessToken?: string
): Promise<File> {
    try {
        const headers: HeadersInit = {};

        // Add authorization header if token is provided
        if (accessToken) {
            headers['Authorization'] = `Bearer ${accessToken}`;
        }

        const response = await fetch(downloadUrl, { headers });

        if (!response.ok) {
            throw new Error(`Failed to download file: ${response.statusText}`);
        }

        const blob = await response.blob();

        // Create a File object from the blob
        return new File([blob], filename, { type: blob.type });
    } catch (error) {
        console.error(`Error downloading file ${filename}:`, error);
        throw error;
    }
}

/**
 * Parse SharePoint path into site path and folder path
 * @param fullPath Full SharePoint URL like "https://tenant.sharepoint.com/sites/SiteName/Shared Documents/Folder/Subfolder"
 * @returns Object with sitePath and folderPath
 */
export function parseSharePointPath(fullPath: string): {
    sitePath: string;
    folderPath: string;
} {
    if (!fullPath) {
        return { sitePath: '', folderPath: '' };
    }

    try {
        const url = new URL(fullPath);
        const pathname = url.pathname;

        // Find the document library (usually "Shared Documents")
        const sharedDocsIndex = pathname.indexOf('Shared Documents');

        if (sharedDocsIndex === -1) {
            // If no standard library found, try to parse as best as possible
            const pathParts = pathname.split('/').filter(p => p);
            if (pathParts.length >= 2) {
                // Assume format: /sites/SiteName/...
                return {
                    sitePath: `/${pathParts[0]}/${pathParts[1]}`,
                    folderPath: '/',
                };
            }
            return { sitePath: pathname, folderPath: '/' };
        }

        // Split at "Shared Documents"
        const beforeSharedDocs = pathname.substring(0, sharedDocsIndex - 1);
        const afterSharedDocs = pathname.substring(sharedDocsIndex + 'Shared Documents'.length);

        return {
            sitePath: beforeSharedDocs + '/Shared Documents',
            folderPath: afterSharedDocs || '/',
        };
    } catch (error) {
        console.error('Error parsing SharePoint path:', error);
        return { sitePath: '', folderPath: '' };
    }
}

/**
 * Extract basic file identifiers from FilePicker item
 * @param item FilePicker item from the pick command
 * @returns File identifiers (driveId and itemId)
 */
export function extractFileMetadata(item: any): {
    name: string;
    downloadUrl: string;
    size?: number;
    webUrl?: string;
    driveId?: string;
    itemId?: string;
} {
    return {
        name: item.name || 'unknown',
        downloadUrl: item['@microsoft.graph.downloadUrl'] || '',
        size: item.size,
        webUrl: item.webUrl,
        driveId: item.parentReference?.driveId,
        itemId: item.id,
    };
}

/**
 * Fetch file metadata from Graph API using driveId and itemId
 * @param driveId The SharePoint drive ID
 * @param itemId The file item ID
 * @param accessToken Graph API access token
 * @returns Complete file metadata including download URL, or null if it's a folder
 */
export async function fetchFileMetadataFromGraph(
    driveId: string,
    itemId: string,
    accessToken: string
): Promise<{
    name: string;
    downloadUrl: string;
    size: number;
    webUrl: string;
    isFolder: boolean;
} | null> {
    const graphUrl = `https://graph.microsoft.com/v1.0/drives/${driveId}/items/${itemId}`;

    console.log('Fetching file metadata from Graph API:', graphUrl);

    const response = await fetch(graphUrl, {
        headers: {
            'Authorization': `Bearer ${accessToken}`,
        },
    });

    if (!response.ok) {
        const errorText = await response.text();
        console.error('Graph API error response:', errorText);
        throw new Error(`Failed to fetch file metadata: ${response.statusText}`);
    }

    const fileData = await response.json();

    console.log('File metadata from Graph:', fileData);

    // Check if this is a folder
    if (fileData.folder) {
        console.log(`Item "${fileData.name}" is a folder, skipping...`);
        return null;
    }

    return {
        name: fileData.name,
        downloadUrl: fileData['@microsoft.graph.downloadUrl'],
        size: fileData.size,
        webUrl: fileData.webUrl,
        isFolder: false,
    };
}/**
 * Extract SharePoint identifiers from FilePicker pick command
 * @param pickData The full pick command data from FilePicker
 * @returns SharePoint identifiers needed for accessing the location
 */
export function extractSharePointIdentifiers(pickData: any): {
    sharepointsiteid: string;
    sharepointlibraryid: string;
    sharepointfolderpath: string;
    endpoint?: string;
} | null {
    try {
        // Extract from the first item
        const item = pickData.items?.[0];
        if (!item) {
            console.error('No items found in pick data');
            return null;
        }

        // Get endpoint (e.g., "https://kapitolgroupcomau.sharepoint.com/_api/v2.0")
        const endpoint = item['@sharePoint.endpoint'];
        if (!endpoint) {
            console.error('No SharePoint endpoint found');
            return null;
        }

        // Extract domain from endpoint (e.g., "kapitolgroupcomau.sharepoint.com")
        const domain = endpoint.replace('https://', '').replace('/_api/v2.0', '');

        // Get SharePoint IDs from the item
        const sharepointIds = item.sharepointIds;
        if (!sharepointIds) {
            console.error('No sharepointIds found in item');
            return null;
        }

        const { siteId, webId } = sharepointIds;
        if (!siteId || !webId) {
            console.error('Missing required SharePoint IDs (siteId or webId)');
            return null;
        }

        // Construct the composite site ID: domain,siteId,webId
        const sharepointsiteid = `${domain},${siteId},${webId}`;

        // Get the library (drive) ID from parentReference
        const driveId = item.parentReference?.driveId;
        if (!driveId) {
            console.error('No driveId found in parentReference');
            return null;
        }

        // The library ID is the driveId
        const sharepointlibraryid = driveId;

        // Try to get folder path from various possible locations
        let folderPath = '';

        // Priority 1: Check if there's a path in sharePoint object (this is the most reliable)
        if (item.sharePoint?.path) {
            folderPath = item.sharePoint.path;
        }
        // Priority 2: Check webUrl and try to parse it
        else if (item.webUrl) {
            // Parse the webUrl to extract the path
            try {
                const url = new URL(item.webUrl);
                // Try to extract path after "/Shared Documents" or similar
                const pathMatch = url.pathname.match(/\/Shared Documents(.*)/i);
                if (pathMatch && pathMatch[1]) {
                    folderPath = decodeURIComponent(pathMatch[1]);
                } else {
                    // If no match, use the full pathname after the site
                    const siteUrlMatch = url.pathname.match(/\/sites\/[^\/]+\/(.*)/);
                    if (siteUrlMatch && siteUrlMatch[1]) {
                        folderPath = '/' + decodeURIComponent(siteUrlMatch[1]);
                    }
                }
            } catch (urlError) {
                console.warn('Failed to parse webUrl:', urlError);
            }
        }
        // Priority 3: Check if there's a folder property
        else if (item.folder?.path) {
            folderPath = item.folder.path;
        }
        // Priority 4: If we have a name property, it might be part of the path
        else if (item.name) {
            folderPath = '/' + item.name;
        }

        // Ensure folder path starts with /
        if (folderPath && !folderPath.startsWith('/')) {
            folderPath = '/' + folderPath;
        }

        console.log('SharePoint extraction debug:', {
            sharepointsiteid,
            sharepointlibraryid,
            sharepointfolderpath: folderPath,
            availableFields: {
                hasSharePointPath: !!item.sharePoint?.path,
                hasWebUrl: !!item.webUrl,
                hasFolderPath: !!item.folder?.path,
                hasName: !!item.name
            }
        });

        return {
            sharepointsiteid,
            sharepointlibraryid,
            sharepointfolderpath: folderPath,
            endpoint,
        };
    } catch (error) {
        console.error('Error extracting SharePoint identifiers:', error);
        return null;
    }
}

/**
 * Construct a SharePoint folder URL from identifiers
 * @param siteId The composite site ID (domain,siteId,webId)
 * @param libraryId The library/drive ID
 * @param folderPath The folder path
 * @returns A SharePoint URL that can be used to browse the folder
 */
export function constructSharePointUrl(
    siteId: string,
    libraryId: string,
    folderPath: string
): string {
    // Extract domain from composite site ID
    const domain = siteId.split(',')[0];

    // Construct the URL using the Graph API format
    // This creates a URL that opens the folder in SharePoint
    const encodedPath = encodeURIComponent(folderPath);
    return `https://${domain}/_layouts/15/Doc.aspx?sourcedoc=${libraryId}&path=${encodedPath}`;
}

/**
 * Construct a Microsoft Graph API URL for accessing a folder
 * @param siteId The composite site ID (domain,siteId,webId)
 * @param libraryId The library/drive ID  
 * @param folderPath The folder path
 * @returns A Graph API URL for accessing the folder
 */
export function constructGraphApiUrl(
    siteId: string,
    libraryId: string,
    folderPath: string
): string {
    // Format: https://graph.microsoft.com/v1.0/drives/{driveId}/root:{folderPath}
    const encodedPath = encodeURIComponent(folderPath);
    return `https://graph.microsoft.com/v1.0/drives/${libraryId}/root:${encodedPath}`;
}

/**
 * Get a display-friendly description of a SharePoint location
 * @param siteId The composite site ID
 * @param libraryId The library/drive ID
 * @param folderPath The folder path
 * @returns A human-readable description
 */
export function getSharePointLocationDescription(
    siteId: string,
    libraryId: string,
    folderPath: string
): string {
    const domain = siteId.split(',')[0];
    const siteName = domain.split('.')[0]; // e.g., "kapitolgroupcomau"

    if (folderPath) {
        return `${siteName}: ${folderPath}`;
    } else {
        return `${siteName} (root)`;
    }
}

/**
 * Fetch the full path of a SharePoint item using Microsoft Graph API
 * @param driveId The drive/library ID
 * @param itemId The item ID
 * @param accessToken The access token for Graph API
 * @returns The full server-relative path of the item
 */
export async function fetchItemPathFromGraph(
    driveId: string,
    itemId: string,
    accessToken: string
): Promise<string | null> {
    try {
        // Query Graph API for the item details
        // Format: https://graph.microsoft.com/v1.0/drives/{driveId}/items/{itemId}
        const graphUrl = `https://graph.microsoft.com/v1.0/drives/${driveId}/items/${itemId}`;

        console.log('Fetching item path from Graph API:', graphUrl);

        const response = await fetch(graphUrl, {
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Accept': 'application/json',
            },
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Graph API error:', response.status, errorText);
            throw new Error(`Graph API request failed: ${response.status} ${response.statusText}`);
        }

        const itemData = await response.json();

        console.log('Graph API response:', itemData);

        // The path can be found in several places:
        // 1. itemData.parentReference.path - gives the parent path
        // 2. itemData.name - the item name
        // 3. Combine them for full path

        let fullPath = '';

        if (itemData.parentReference?.path) {
            // Path format from Graph: "/drive/root:/path/to/parent"
            // We need to extract just the "/path/to/parent" part
            const parentPath = itemData.parentReference.path;

            // Remove "/drive/root:" prefix if present
            const cleanPath = parentPath.replace('/drive/root:', '') || '/';

            // Append the item name if this is a folder
            if (itemData.folder && itemData.name) {
                fullPath = cleanPath === '/' ? `/${itemData.name}` : `${cleanPath}/${itemData.name}`;
            } else {
                fullPath = cleanPath;
            }
        } else if (itemData.name) {
            // If no parent path, assume root level
            fullPath = `/${itemData.name}`;
        }

        console.log('Extracted path from Graph API:', fullPath);

        return fullPath;
    } catch (error) {
        console.error('Error fetching item path from Graph API:', error);
        return null;
    }
}

/**
 * Extract SharePoint identifiers from FilePicker pick command and optionally fetch the path using Graph API
 * @param pickData The full pick command data from FilePicker
 * @param accessToken Optional access token to fetch path from Graph API if not available in pick data
 * @returns SharePoint identifiers with path (either from pick data or fetched from Graph)
 */
export async function extractSharePointIdentifiersWithPath(
    pickData: any,
    accessToken?: string
): Promise<{
    sharepointsiteid: string;
    sharepointlibraryid: string;
    sharepointfolderpath: string;
    endpoint?: string;
    pathSource: 'pickData' | 'graphApi' | 'unavailable';
} | null> {
    try {
        // First, extract the basic identifiers
        const basicIdentifiers = extractSharePointIdentifiers(pickData);

        if (!basicIdentifiers) {
            return null;
        }

        // If we already have a path, return it
        if (basicIdentifiers.sharepointfolderpath) {
            return {
                ...basicIdentifiers,
                pathSource: 'pickData',
            };
        }

        // If no path and we have an access token, try to fetch it from Graph API
        if (accessToken) {
            const item = pickData.items?.[0];
            const itemId = item?.id;
            const driveId = basicIdentifiers.sharepointlibraryid;

            if (itemId && driveId) {
                console.log('Path not in pick data, fetching from Graph API...');
                const graphPath = await fetchItemPathFromGraph(driveId, itemId, accessToken);

                if (graphPath) {
                    return {
                        ...basicIdentifiers,
                        sharepointfolderpath: graphPath,
                        pathSource: 'graphApi',
                    };
                }
            }
        }

        // No path available
        return {
            ...basicIdentifiers,
            pathSource: 'unavailable',
        };
    } catch (error) {
        console.error('Error extracting SharePoint identifiers with path:', error);
        return null;
    }
}
