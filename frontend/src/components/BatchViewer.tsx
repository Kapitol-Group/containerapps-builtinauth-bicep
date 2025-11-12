import React, { useState } from 'react';
import { Batch, TenderFile } from '../types';
import FileBrowser from './FileBrowser';
import './BatchViewer.css';

interface BatchViewerProps {
    batch: Batch;
    files: TenderFile[];
    tenderId: string;
    onClose: () => void;
    onFileSelect: (file: TenderFile) => void;
    loading?: boolean;
}

const BatchViewer: React.FC<BatchViewerProps> = ({
    batch,
    files,
    tenderId,
    onClose,
    onFileSelect,
    loading = false,
}) => {
    const [selectedFile, setSelectedFile] = useState<TenderFile | null>(null);
    const [retrying, setRetrying] = useState(false);

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
            const response = await fetch(
                `/api/tenders/${tenderId}/batches/${batch.batch_id}/retry`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                }
            );

            const data = await response.json();

            if (data.success) {
                alert('Batch retry initiated. Processing in background.');
                onClose(); // Return to batch list
            } else {
                alert(`Retry failed: ${data.error}`);
            }
        } catch (error) {
            console.error('Error retrying batch:', error);
            alert('Failed to retry batch. Please try again.');
        } finally {
            setRetrying(false);
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

            <div className="batch-files-section">
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
        </div>
    );
};

export default BatchViewer;
