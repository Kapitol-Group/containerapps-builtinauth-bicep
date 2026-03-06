import React, { useEffect, useRef, useState } from 'react';
import { mfilesApi } from '../services/api';
import { MFilesImportDocument } from '../types';
import MFilesFilePickerDialog from './MFilesFilePickerDialog';
import './MFilesFileBrowser.css';

interface MFilesFileBrowserProps {
  tenderId: string;
  projectName: string;
  onFilesImported: () => void;
}

const MFilesFileBrowser: React.FC<MFilesFileBrowserProps> = ({
  tenderId,
  projectName,
  onFilesImported,
}) => {
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importProgress, setImportProgress] = useState<{
    current: number;
    total: number;
    currentFile: string;
    status: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const handleImportSelected = async (documents: MFilesImportDocument[]) => {
    if (!documents.length) {
      return;
    }

    setError(null);
    setIsImporting(true);
    setImportProgress({
      current: 0,
      total: documents.length,
      currentFile: 'Starting import...',
      status: 'running',
    });

    try {
      const importResult = await mfilesApi.importFiles(tenderId, documents, 'mfiles-import');
      setIsPickerOpen(false);
      startPolling(importResult.job_id);
    } catch (error) {
      setIsImporting(false);
      setImportProgress(null);
      throw error;
    }
  };

  const startPolling = (jobId: string) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const status = await mfilesApi.getImportJobStatus(jobId);

        setImportProgress({
          current: status.progress,
          total: status.total,
          currentFile: status.current_file || 'Processing...',
          status: status.status,
        });

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
            setError(`Import completed with errors:\n${status.errors.join('\n')}\n\nSuccessfully imported ${status.success_count} of ${status.total} documents.`);
            onFilesImported();
          } else {
            onFilesImported();
          }
        }
      } catch {
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
    <div className="mfiles-file-browser">
      {!isImporting ? (
        <>
          <button
            type="button"
            className="mfiles-browse-btn btn-secondary"
            onClick={() => {
              setError(null);
              setIsPickerOpen(true);
            }}
          >
            Browse M-Files
          </button>

          <MFilesFilePickerDialog
            isOpen={isPickerOpen}
            tenderId={tenderId}
            projectName={projectName}
            onClose={() => setIsPickerOpen(false)}
            onImportSelected={handleImportSelected}
          />
        </>
      ) : (
        <div className="import-progress">
          <div className="progress-spinner"></div>
          <div className="progress-text">
            {importProgress && (
              <>
                <p>Importing files from M-Files...</p>
                <p className="progress-detail">
                  {importProgress.current} of {importProgress.total}: {importProgress.currentFile}
                </p>
                {importProgress.status === 'completed_with_errors' && (
                  <p className="progress-warning">Some documents failed to import.</p>
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
          <button type="button" onClick={() => setError(null)} className="btn-dismiss">Dismiss</button>
        </div>
      )}
    </div>
  );
};

export default MFilesFileBrowser;
