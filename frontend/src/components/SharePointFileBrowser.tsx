import React, { useState, useEffect, useRef } from 'react';
import { SharePointFilePicker } from './SharePointFilePicker';
import { sharepointApi } from '../services/api';
import { extractFileMetadata, fetchFileMetadataFromGraph, fetchFolderContentsRecursive } from '../utils/sharepoint';
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
  const [isScanning, setIsScanning] = useState(false);
  const [importProgress, setImportProgress] = useState<{
    current: number;
    total: number;
    currentFile: string;
    status: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

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

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const handleFilePicked = async (data: any) => {
    console.log('SharePoint items picked:', data);
    
    if (!data.items || data.items.length === 0) {
      console.log('No items selected');
      return;
    }

    // Log the first item to see its structure
    console.log('First item structure:', JSON.stringify(data.items[0], null, 2));

    setIsScanning(true);
    setError(null);

    try {
      // Get Graph API access token
      let graphToken: string | undefined;
      try {
        graphToken = await getGraphApiToken('https://graph.microsoft.com');
        console.log('Got Graph API token for SharePoint operations');
      } catch (tokenError) {
        console.error('Failed to get Graph API token:', tokenError);
        setError('Failed to authenticate with Microsoft Graph. Cannot access SharePoint files.');
        setIsScanning(false);
        return;
      }

      if (!graphToken) {
        setError('Failed to get Graph API access token.');
        setIsScanning(false);
        return;
      }

      // Build list of all files (including from folders)
      const allFiles: Array<{
        name: string;
        downloadUrl: string;
        driveId: string;
        itemId: string;
        relativePath?: string;
        size?: number;
        mimeType?: string;
      }> = [];

      for (const item of data.items) {
        const basicMetadata = extractFileMetadata(item);
        
        console.log('Processing item:', basicMetadata.name);

        if (!basicMetadata.driveId || !basicMetadata.itemId) {
          console.error('Missing driveId or itemId for item:', item);
          continue;
        }

        // Fetch metadata from Graph API to determine if it's a folder or file
        try {
          const itemMetadata = await fetchFileMetadataFromGraph(
            basicMetadata.driveId,
            basicMetadata.itemId,
            graphToken
          );

          // If metadata is null, it's a folder
          if (!itemMetadata) {
            // It's a folder - recursively fetch all files
            console.log(`Item "${basicMetadata.name}" is a folder, fetching contents...`);
            
            try {
              const folderFiles = await fetchFolderContentsRecursive(
                basicMetadata.driveId,
                basicMetadata.itemId,
                graphToken,
                basicMetadata.name
              );
              
              console.log(`Found ${folderFiles.length} files in folder "${basicMetadata.name}"`);
              allFiles.push(...folderFiles);
            } catch (folderError) {
              console.error(`Failed to fetch contents of folder "${basicMetadata.name}":`, folderError);
              setError(`Failed to scan folder "${basicMetadata.name}": ${folderError instanceof Error ? folderError.message : 'Unknown error'}`);
            }
          } else {
            // It's a file - add directly
            console.log(`Item "${itemMetadata.name}" is a file`);
            
            if (itemMetadata.downloadUrl) {
              allFiles.push({
                name: itemMetadata.name,
                downloadUrl: itemMetadata.downloadUrl,
                driveId: basicMetadata.driveId,
                itemId: basicMetadata.itemId,
                size: itemMetadata.size,
              });
            }
          }
        } catch (metadataError) {
          console.error(`Failed to fetch metadata for "${basicMetadata.name}":`, metadataError);
          continue;
        }
      }

      console.log(`Total files to import: ${allFiles.length}`);

      if (allFiles.length === 0) {
        setError('No files found to import');
        setIsScanning(false);
        return;
      }

      // Send to backend for import
      setIsScanning(false);
      setIsImporting(true);
      setImportProgress({
        current: 0,
        total: allFiles.length,
        currentFile: 'Starting import...',
        status: 'running'
      });

      const result = await sharepointApi.importFiles(
        tenderId,
        graphToken,
        allFiles,
        'sharepoint-import'
      );

      console.log('Import job started:', result.job_id);

      // Start polling for progress
      startPolling(result.job_id);

    } catch (err) {
      console.error('Error during SharePoint import:', err);
      setError(err instanceof Error ? err.message : 'Failed to import files from SharePoint');
      setIsScanning(false);
      setIsImporting(false);
      setImportProgress(null);
    }
  };

  const startPolling = (jobId: string) => {
    // Clear any existing polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    // Poll every 1.5 seconds
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const status = await sharepointApi.getImportJobStatus(jobId);
        
        setImportProgress({
          current: status.progress,
          total: status.total,
          currentFile: status.current_file || 'Processing...',
          status: status.status
        });

        // Stop polling if job is complete
        if (status.status === 'completed' || status.status === 'completed_with_errors' || status.status === 'failed') {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }

          setIsImporting(false);
          setImportProgress(null);

          if (status.status === 'failed') {
            setError(`Import failed: ${status.errors.join(', ')}`);
          } else if (status.status === 'completed_with_errors') {
            setError(`Import completed with errors:\n${status.errors.join('\n')}\n\nSuccessfully imported ${status.success_count} of ${status.total} files.`);
          } else {
            console.log(`Successfully imported ${status.success_count} files from SharePoint`);
          }

          // Refresh file list
          onFilesImported();
        }
      } catch (pollError) {
        console.error('Error polling import status:', pollError);
        
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        
        setIsImporting(false);
        setImportProgress(null);
        setError('Lost connection to import job. Files may still be importing in the background.');
      }
    }, 1500);
  };

  return (
    <div className="sharepoint-file-browser">
      {!isImporting && !isScanning ? (
        <SharePointFilePicker
          baseUrl={sharepointBaseUrl}
          tenderSitePath={sitePath}
          tenderFolder={folderPath}
          onFilePicked={handleFilePicked}
          buttonText="Browse SharePoint"
          className="sharepoint-browse-btn"
          filters={[]}
        />
      ) : isScanning ? (
        <div className="import-progress">
          <div className="progress-spinner"></div>
          <div className="progress-text">
            <p>Scanning SharePoint folders...</p>
            <p className="progress-detail">Finding files to import...</p>
          </div>
        </div>
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
                {importProgress.status === 'completed_with_errors' && (
                  <p className="progress-warning">Some files failed to import</p>
                )}
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
