import React, { useState, useEffect, useRef } from 'react';
import { Batch, TenderFile } from '../types';
import { batchesApi } from '../services/api';
import FileBrowser from './FileBrowser';
import './BatchViewer.css';

interface BatchViewerProps {
    batch: Batch;
    files: TenderFile[];
    tenderId: string;
    onClose: () => void;
    onFileSelect: (file: TenderFile) => void;
    loading?: boolean;
    onError?: (message: string) => void;
    onRetry?: () => void;
    onDelete?: () => void;
}

interface FileProgress {
    filename: string;
    status: 'queued' | 'extracted' | 'failed' | 'exported';
    drawing_number: string | null;
    drawing_revision: string | null;
    drawing_title: string | null;
    destination_path: string | null;
    created_at: string | null;
    updated_at: string | null;
}

const BatchViewer: React.FC<BatchViewerProps> = ({
    batch,
    files,
    tenderId,
    onClose,
    onFileSelect,
    loading = false,
    onError,
    onRetry,
    onDelete,
}) => {
    const [selectedFile, setSelectedFile] = useState<TenderFile | null>(null);
    const [retrying, setRetrying] = useState(false);
    const [fileProgress, setFileProgress] = useState<FileProgress[]>([]);
    const [loadingProgress, setLoadingProgress] = useState(false);
    const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
    
    // Get polling interval from environment or default to 30 seconds
    const pollingInterval = parseInt(
        (window as any).BATCH_PROGRESS_POLLING_INTERVAL || '30000',
        10
    );

    // Load and poll file progress for running batches
    useEffect(() => {
        const loadProgress = async () => {
            if (!batch.uipath_reference) {
                // Batch not yet submitted to UiPath
                return;
            }

            try {
                setLoadingProgress(true);
                const progress = await batchesApi.getProgress(tenderId, batch.batch_id);
                setFileProgress(progress.files);
            } catch (error: any) {
                console.error('Failed to load batch progress:', error);
                if (onError) {
                    onError('Failed to load batch progress');
                }
            } finally {
                setLoadingProgress(false);
            }
        };

        // Initial load
        loadProgress();

        // Poll if batch is running
        if (batch.status === 'running') {
            pollingIntervalRef.current = setInterval(loadProgress, pollingInterval);
        }

        // Cleanup
        return () => {
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
            }
        };
    }, [batch.batch_id, batch.status, batch.uipath_reference, tenderId, pollingInterval, onError]);

    const handleFileSelect = (file: TenderFile) => {
        setSelectedFile(file);
        onFileSelect(file);
    };

    const handleRetry = async () => {
        if (!confirm('Retry submission for this batch? This will resubmit the extraction job to UiPath.')) {
            return;
        }

        setRetrying(true);
        try {
            await batchesApi.retry(tenderId, batch.batch_id);
            if (onRetry) {
                onRetry();
            }
            onClose(); // Return to batch list
        } catch (error: any) {
            console.error('Error retrying batch:', error);
            if (onError) {
                onError(error.message || 'Failed to retry batch. Please try again.');
            }
        } finally {
            setRetrying(false);
        }
    };

    const handleDelete = async () => {
        if (!confirm('Are you sure you want to delete this batch? Files will remain categorized.')) {
            return;
        }

        if (onDelete) {
            onDelete();
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'exported':
                return '✓';
            case 'extracted':
                return '⏳';
            case 'failed':
                return '✗';
            case 'queued':
                return '⋯';
            default:
                return '?';
        }
    };

    const getStatusClass = (status: string) => {
        switch (status) {
            case 'exported':
                return 'file-status-exported';
            case 'extracted':
                return 'file-status-extracted';
            case 'failed':
                return 'file-status-failed';
            case 'queued':
                return 'file-status-queued';
            default:
                return '';
        }
    };

    const formatDate = (dateString: string) => {
        try {
            const date = new Date(dateString);
            return date.toLocaleString();
        } catch {
            return dateString;
        }
    };

    const getStatusBadgeClass = (status: string) => {
        switch (status) {
            case 'pending':
                return 'status-pending';
            case 'running':
                return 'status-running';
            case 'completed':
                return 'status-completed';
            case 'failed':
                return 'status-failed';
            default:
                return '';
        }
    };

    const canRetry = batch.status === 'failed' || batch.status === 'pending';

    if (loading) {
        return (
            <div className="batch-viewer-loading">
                <p>Loading batch details...</p>
            </div>
        );
    }

    return (
        <div className="batch-viewer">
            <div className="batch-viewer-header">
                <button className="close-button" onClick={onClose}>
                    ← Back to Batches
                </button>
                <div className="header-info">
                    <h2 className="batch-viewer-title">{batch.batch_name}</h2>
                    <div className="header-metadata">
                        <span className={`status-badge ${getStatusBadgeClass(batch.status)}`}>
                            {batch.status}
                        </span>
                        <span className="metadata-item">
                            <strong>Discipline:</strong> {batch.discipline}
                        </span>
                        <span className="metadata-item">
                            <strong>Files:</strong> {batch.file_count}
                        </span>
                        <span className="metadata-item">
                            <strong>Submitted:</strong> {formatDate(batch.submitted_at)} by {batch.submitted_by}
                        </span>
                        {batch.job_id && (
                            <span className="metadata-item job-id-item">
                                <strong>Job ID:</strong> {batch.job_id}
                            </span>
                        )}
                        {batch.uipath_reference && (
                            <span className="metadata-item">
                                <strong>UiPath Ref:</strong> {batch.uipath_reference}
                            </span>
                        )}
                        <span className="metadata-item coords-item">
                            <strong>Title Block:</strong> X:{batch.title_block_coords.x} Y:{batch.title_block_coords.y} 
                            {' '}W:{batch.title_block_coords.width} H:{batch.title_block_coords.height}
                        </span>
                    </div>
                    {canRetry && (
                        <button
                            className="retry-button"
                            onClick={handleRetry}
                            disabled={retrying}
                        >
                            {retrying ? 'Retrying...' : '🔄 Retry Submission'}
                        </button>
                    )}
                </div>
            </div>

            {/* Display submission attempts history if available */}
            {batch.submission_attempts && batch.submission_attempts.length > 0 && (
                <div className="submission-history">
                    <h3>Submission Attempts</h3>
                    <div className="attempts-list">
                        {batch.submission_attempts.map((attempt, index) => (
                            <div key={index} className={`attempt-item attempt-${attempt.status}`}>
                                <span className="attempt-number">#{index + 1}</span>
                                <span className="attempt-time">{formatDate(attempt.timestamp)}</span>
                                <span className={`attempt-status status-${attempt.status}`}>
                                    {attempt.status}
                                </span>
                                {attempt.reference && (
                                    <span className="attempt-reference">Ref: {attempt.reference}</span>
                                )}
                                {attempt.error && (
                                    <span className="attempt-error" title={attempt.error}>
                                        ⚠️ {attempt.error.substring(0, 50)}{attempt.error.length > 50 ? '...' : ''}
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Display last error if available */}
            {batch.last_error && (
                <div className="last-error-box">
                    <h4>⚠️ Last Error</h4>
                    <p>{batch.last_error}</p>
                </div>
            )}

            {/* File-level progress display */}
            {fileProgress.length > 0 && (
                <div className="file-progress-section">
                    <h3>File Processing Status</h3>
                    {loadingProgress && <p className="loading-indicator">Updating...</p>}
                    <div className="file-progress-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>Status</th>
                                    <th>Filename</th>
                                    <th>Drawing Number</th>
                                    <th>Revision</th>
                                    <th>Title</th>
                                    <th>Updated</th>
                                </tr>
                            </thead>
                            <tbody>
                                {fileProgress.map((file, index) => (
                                    <tr key={index} className={getStatusClass(file.status)}>
                                        <td className="status-cell">
                                            <span className="status-icon">{getStatusIcon(file.status)}</span>
                                            <span className="status-text">{file.status}</span>
                                        </td>
                                        <td className="filename-cell">{file.filename}</td>
                                        <td>{file.drawing_number || '-'}</td>
                                        <td>{file.drawing_revision || '-'}</td>
                                        <td className="title-cell">{file.drawing_title || '-'}</td>
                                        <td className="time-cell">
                                            {file.updated_at ? formatDate(file.updated_at) : '-'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            <div className="batch-files-section">
                <h3>Batch Files</h3>
                <FileBrowser
                    files={files}
                    selectedFile={selectedFile}
                    selectedFiles={[]}
                    onFileSelect={handleFileSelect}
                    onSelectionChange={() => {}} // No multi-selection in read-only mode
                    onFileDelete={undefined} // No deletion in read-only mode
                    loading={false}
                    readOnly={true}
                />
            </div>

            {canRetry && onDelete && (
                <div className="batch-actions">
                    <button
                        className="delete-button"
                        onClick={handleDelete}
                    >
                        🗑️ Delete Batch
                    </button>
                </div>
            )}
        </div>
    );
};

export default BatchViewer;
