import React, { useState } from 'react';
import { SharePointFilePicker } from './SharePointFilePicker';
import { filesApi } from '../services/api';
import { downloadFileFromSharePoint, extractFileMetadata, fetchFileMetadataFromGraph } from '../utils/sharepoint';
import { getGraphApiToken } from '../authConfig';
import './SharePointFileBrowser.css';

interface SharePointFileBrowserProps {
  tenderId: string;
  defaultSharePointPath?: string;
  sharepointBaseUrl: string;
  onFilesImported: () => void;
}

export const SharePointFileBrowser: React.FC<SharePointFileBrowserProps> = ({
  tenderId,
  defaultSharePointPath,
  sharepointBaseUrl,
  onFilesImported,
}) => {
  const [isImporting, setIsImporting] = useState(false);
  const [importProgress, setImportProgress] = useState<{
    current: number;
    total: number;
    currentFile: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Default site path - this should match what's used in SharePointFilePicker
  const defaultSitePath = '/sites/KapitolGroupNewBusinessTeam/Shared Documents';
  
  // Extract the folder path from the stored path
  // If it contains "/root:" from Graph API, extract only the portion after that
  let folderPath = defaultSharePointPath || '/01 TENDERS/Active/';
  if (folderPath.includes('/root:')) {
    const parts = folderPath.split('/root:');
    folderPath = parts[1] || '/01 TENDERS/Active/';
  }
  
  const sitePath = defaultSitePath;
  
  console.log('Using SharePoint site path:', sitePath);
  console.log('Using SharePoint folder path:', folderPath);

  const handleFilePicked = async (data: any) => {
    console.log('SharePoint files picked:', data);
    
    if (!data.items || data.items.length === 0) {
      console.log('No files selected');
      return;
    }

    // Log the first item to see its structure
    console.log('First item structure:', JSON.stringify(data.items[0], null, 2));

    setIsImporting(true);
    setError(null);
    setImportProgress({ current: 0, total: data.items.length, currentFile: '' });

    const errors: string[] = [];
    let successCount = 0;

    try {
      // Get Graph API access token
      let graphToken: string | undefined;
      try {
        graphToken = await getGraphApiToken('https://graph.microsoft.com');
        console.log('Got Graph API token for file download');
      } catch (tokenError) {
        console.error('Failed to get Graph API token:', tokenError);
        setError('Failed to authenticate with Microsoft Graph. Cannot download files.');
        setIsImporting(false);
        setImportProgress(null);
        return;
      }

      if (!graphToken) {
        setError('Failed to get Graph API access token.');
        setIsImporting(false);
        setImportProgress(null);
        return;
      }

      for (let i = 0; i < data.items.length; i++) {
        const item = data.items[i];
        const basicMetadata = extractFileMetadata(item);
        
        console.log('Basic metadata:', basicMetadata);

        // We need to fetch the full metadata from Graph API to get the download URL
        if (!basicMetadata.driveId || !basicMetadata.itemId) {
          console.error('Missing driveId or itemId for item:', item);
          errors.push(`${basicMetadata.name || 'Unknown file'}: Missing file identifiers`);
          continue;
        }

        try {
          // Fetch complete file metadata from Graph API
          console.log(`Fetching metadata for ${basicMetadata.name || 'file'} from Graph API...`);
          const fileMetadata = await fetchFileMetadataFromGraph(
            basicMetadata.driveId,
            basicMetadata.itemId,
            graphToken
          );

          // Skip if it's a folder
          if (!fileMetadata) {
            console.log(`Skipping folder: ${basicMetadata.name || 'unknown'}`);
            continue;
          }

          setImportProgress({
            current: i + 1,
            total: data.items.length,
            currentFile: fileMetadata.name,
          });

          // Validate we have a download URL
          if (!fileMetadata.downloadUrl) {
            throw new Error('No download URL available for this file');
          }

          // Download file from SharePoint
          console.log(`Downloading ${fileMetadata.name} from SharePoint...`);
          console.log(`Download URL: ${fileMetadata.downloadUrl}`);
          const file = await downloadFileFromSharePoint(
            fileMetadata.downloadUrl,
            fileMetadata.name
          );

          // Upload to backend
          console.log(`Uploading ${fileMetadata.name} to tender ${tenderId}...`);
          await filesApi.upload(tenderId, file, 'sharepoint-import', 'sharepoint');
          
          successCount++;
        } catch (err) {
          console.error(`Failed to import ${basicMetadata.name}:`, err);
          errors.push(`${basicMetadata.name}: ${err instanceof Error ? err.message : 'Unknown error'}`);
        }
      }

      if (errors.length > 0) {
        setError(`Imported ${successCount} of ${data.items.length} files. Errors:\n${errors.join('\n')}`);
      } else {
        console.log(`Successfully imported ${successCount} files from SharePoint`);
      }

      // Refresh file list
      onFilesImported();
    } catch (err) {
      console.error('Error during SharePoint import:', err);
      setError(err instanceof Error ? err.message : 'Failed to import files from SharePoint');
    } finally {
      setIsImporting(false);
      setImportProgress(null);
    }
  };

  return (
    <div className="sharepoint-file-browser">
      {!isImporting ? (
        <SharePointFilePicker
          baseUrl={sharepointBaseUrl}
          tenderSitePath={sitePath}
          tenderFolder={folderPath}
          onFilePicked={handleFilePicked}
          buttonText="Browse SharePoint"
          className="sharepoint-browse-btn"
          filters={[]}
        />
      ) : (
        <div className="import-progress">
          <div className="progress-spinner"></div>
          <div className="progress-text">
            {importProgress && (
              <>
                <p>Importing files from SharePoint...</p>
                <p className="progress-detail">
                  {importProgress.current} of {importProgress.total}: {importProgress.currentFile}
                </p>
              </>
            )}
          </div>
        </div>
      )}
      
      {error && (
        <div className="import-error">
          <p className="error-title">Import Error</p>
          <pre className="error-message">{error}</pre>
          <button onClick={() => setError(null)} className="btn-dismiss">Dismiss</button>
        </div>
      )}
    </div>
  );
};

export default SharePointFileBrowser;
