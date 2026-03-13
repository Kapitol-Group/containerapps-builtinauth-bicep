import React, { useEffect, useRef, useState } from 'react';
import {
    Batch,
    BatchMetricSource,
    BatchProgressResponse,
    BatchStatusCounts,
    TenderFile,
} from '../types';
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

const EMPTY_STATUS_COUNTS: BatchStatusCounts = {
    queued: 0,
    extracted: 0,
    failed: 0,
    exported: 0,
};

const formatDate = (dateString?: string | null) => {
    if (!dateString) {
        return '-';
    }

    try {
        return new Date(dateString).toLocaleString();
    } catch {
        return dateString;
    }
};

const formatDuration = (durationSeconds?: number | null) => {
    if (durationSeconds === null || durationSeconds === undefined) {
        return '-';
    }

    const seconds = Math.max(0, Math.round(durationSeconds));
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    if (minutes > 0) {
        return `${minutes}m ${remainingSeconds}s`;
    }
    return `${remainingSeconds}s`;
};

const formatThroughput = (filesPerMinute?: number | null) => {
    if (filesPerMinute === null || filesPerMinute === undefined) {
        return '-';
    }
    return `${filesPerMinute.toFixed(1)} files/min`;
};

const escapeCsvValue = (value: string | null | undefined) => {
    const normalized = value ?? '';
    return `"${normalized.replace(/"/g, '""')}"`;
};

const sanitizeFilenamePart = (value: string) => (
    value
        .trim()
        .replace(/[^a-z0-9-_]+/gi, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '')
);

const isEstimatedMetric = (source?: BatchMetricSource) => source === 'estimated';

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
    const [deleting, setDeleting] = useState(false);
    const [progressData, setProgressData] = useState<BatchProgressResponse | null>(null);
    const [loadingProgress, setLoadingProgress] = useState(false);
    const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const pollingInterval = parseInt(
        (window as any).BATCH_PROGRESS_POLLING_INTERVAL || '30000',
        10
    );

    useEffect(() => {
        let isCancelled = false;

        const stopPolling = () => {
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
            }
        };

        const loadProgress = async () => {
            try {
                setLoadingProgress(true);
                const progress = await batchesApi.getProgress(tenderId, batch.batch_id);
                if (isCancelled) {
                    return;
                }

                setProgressData(progress);

                const hasExactCompletion = Boolean(progress.metrics?.completion?.completed_at);
                const allFilesFinished = (
                    progress.total_files > 0
                    && progress.status_counts.queued === 0
                    && progress.status_counts.extracted === 0
                );
                if (hasExactCompletion || allFilesFinished) {
                    stopPolling();
                }
            } catch (error: any) {
                if (isCancelled) {
                    return;
                }
                console.error('Failed to load batch progress:', error);
                onError?.('Failed to load batch progress');
            } finally {
                if (!isCancelled) {
                    setLoadingProgress(false);
                }
            }
        };

        loadProgress();

        if (batch.status === 'running' || batch.status === 'submitting') {
            pollingIntervalRef.current = setInterval(loadProgress, pollingInterval);
        }

        return () => {
            isCancelled = true;
            stopPolling();
        };
    }, [batch.batch_id, batch.status, tenderId, pollingInterval, onError]);

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
            onRetry?.();
            onClose();
        } catch (error: any) {
            console.error('Error retrying batch:', error);
            onError?.(error.message || 'Failed to retry batch. Please try again.');
        } finally {
            setRetrying(false);
        }
    };

    const handleDelete = async () => {
        if (!confirm(`Are you sure you want to delete batch "${batch.batch_name}"? The batch record will be removed and its files will become uncategorized.`)) {
            return;
        }

        setDeleting(true);
        try {
            await batchesApi.delete(tenderId, batch.batch_id);
            onDelete?.();
        } catch (error: any) {
            console.error('Error deleting batch:', error);
            onError?.(error.message || 'Failed to delete batch. Please try again.');
        } finally {
            setDeleting(false);
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

    const getStatusBadgeClass = (status: string) => {
        switch (status) {
            case 'pending':
                return 'status-pending';
            case 'submitting':
                return 'status-running';
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

    const renderMetricBadge = (source?: BatchMetricSource) => {
        if (!isEstimatedMetric(source)) {
            return null;
        }

        return <span className="metric-badge">Estimated</span>;
    };

    const statusCounts = progressData?.status_counts || {
        ...EMPTY_STATUS_COUNTS,
        queued: batch.file_count,
    };
    const fileProgress = progressData?.files || [];
    const metrics = progressData?.metrics;
    const canRetry = batch.status === 'failed';

    const handleExportCsv = () => {
        if (fileProgress.length === 0) {
            return;
        }

        try {
            const header = [
                'Status',
                'Filename',
                'Drawing Number',
                'Revision',
                'Revision Date',
                'Title',
                'Updated At',
            ];
            const rows = fileProgress.map((file) => [
                file.status,
                file.filename,
                file.drawing_number,
                file.drawing_revision,
                file.revision_date,
                file.drawing_title,
                file.updated_at,
            ]);
            const csvContent = [
                header.map(escapeCsvValue).join(','),
                ...rows.map((row) => row.map((value) => escapeCsvValue(value)).join(',')),
            ].join('\n');

            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            const batchLabel = sanitizeFilenamePart(batch.batch_name || batch.batch_id) || batch.batch_id;

            link.href = url;
            link.download = `${batchLabel}-file-processing-status.csv`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Failed to export file processing status CSV:', error);
            onError?.('Failed to export file processing status CSV');
        }
    };

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

            <div className="batch-metrics-section">
                <div className="section-header">
                    <h3>Batch Metrics</h3>
                    {loadingProgress && <p className="loading-indicator">Updating...</p>}
                </div>
                <div className="metrics-grid">
                    <div className="metric-card">
                        <div className="metric-card-header">
                            <span className="metric-title">Submission</span>
                            {renderMetricBadge(metrics?.submission.source)}
                        </div>
                        <div className="metric-value">{formatDuration(metrics?.submission.duration_seconds)}</div>
                        <div className="metric-meta">
                            {metrics?.submission.attempt_count
                                ? `${metrics.submission.attempt_count} attempt${metrics.submission.attempt_count === 1 ? '' : 's'}`
                                : 'No attempts recorded'}
                        </div>
                    </div>

                    <div className="metric-card">
                        <div className="metric-card-header">
                            <span className="metric-title">Extraction</span>
                            {renderMetricBadge(metrics?.extraction.source)}
                        </div>
                        <div className="metric-value">{formatDuration(metrics?.extraction.duration_seconds)}</div>
                        <div className="metric-meta">
                            {metrics?.extraction.started_at
                                ? `Started ${formatDate(metrics.extraction.started_at)}`
                                : 'No extraction timing yet'}
                        </div>
                    </div>

                    <div className="metric-card">
                        <div className="metric-card-header">
                            <span className="metric-title">Completed</span>
                            {renderMetricBadge(metrics?.completion.source)}
                        </div>
                        <div className="metric-value">{formatDate(metrics?.completion.completed_at)}</div>
                        <div className="metric-meta">
                            {metrics?.completion.completed_at ? 'Terminal batch time' : 'Not completed yet'}
                        </div>
                    </div>

                    <div className="metric-card">
                        <div className="metric-card-header">
                            <span className="metric-title">Total</span>
                            {renderMetricBadge(metrics?.total.source)}
                        </div>
                        <div className="metric-value">{formatDuration(metrics?.total.duration_seconds)}</div>
                        <div className="metric-meta">
                            {metrics?.total.ended_at
                                ? `Last update ${formatDate(metrics.total.ended_at)}`
                                : 'Elapsed total unavailable'}
                        </div>
                    </div>

                    <div className="metric-card">
                        <div className="metric-card-header">
                            <span className="metric-title">Throughput</span>
                            {renderMetricBadge(metrics?.throughput.source)}
                        </div>
                        <div className="metric-value">{formatThroughput(metrics?.throughput.files_per_minute)}</div>
                        <div className="metric-meta">
                            {metrics ? `${metrics.throughput.processed_files} processed` : 'No throughput yet'}
                        </div>
                    </div>
                </div>

                <div className="status-strip">
                    <div className="status-chip status-chip-queued">Queued {statusCounts.queued}</div>
                    <div className="status-chip status-chip-extracted">Extracted {statusCounts.extracted}</div>
                    <div className="status-chip status-chip-failed">Failed {statusCounts.failed}</div>
                    <div className="status-chip status-chip-exported">Exported {statusCounts.exported}</div>
                </div>
            </div>

            {batch.submission_attempts && batch.submission_attempts.length > 0 && (
                <div className="submission-history">
                    <h3>Submission Attempts</h3>
                    <div className="attempts-list">
                        {batch.submission_attempts.map((attempt, index) => (
                            <div key={index} className={`attempt-item attempt-${attempt.status}`}>
                                <span className="attempt-number">#{index + 1}</span>
                                <span className="attempt-time">{formatDate(attempt.started_at || attempt.timestamp)}</span>
                                <span className={`attempt-status status-${attempt.status}`}>
                                    {attempt.status}
                                </span>
                                {attempt.duration_seconds !== undefined && (
                                    <span className="attempt-duration">{formatDuration(attempt.duration_seconds)}</span>
                                )}
                                {attempt.reference && (
                                    <span className="attempt-reference">Ref: {attempt.reference}</span>
                                )}
                                {attempt.error && (
                                    <span className="attempt-error" title={attempt.error}>
                                        ⚠️ {attempt.error.substring(0, 80)}{attempt.error.length > 80 ? '...' : ''}
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {batch.last_error && (
                <div className="last-error-box">
                    <h4>⚠️ Last Error</h4>
                    <p>{batch.last_error}</p>
                </div>
            )}

            {fileProgress.length > 0 && (
                <div className="file-progress-section">
                    <div className="section-header">
                        <h3>File Processing Status</h3>
                        <div className="section-actions">
                            {loadingProgress && <p className="loading-indicator">Updating...</p>}
                            <button
                                type="button"
                                className="export-button"
                                onClick={handleExportCsv}
                            >
                                Export CSV
                            </button>
                        </div>
                    </div>
                    <div className="file-progress-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>Status</th>
                                    <th>Filename</th>
                                    <th>Drawing Number</th>
                                    <th>Revision</th>
                                    <th>Revision Date</th>
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
                                        <td>{file.revision_date || '-'}</td>
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
                    onSelectionChange={() => {}}
                    onFileDelete={undefined}
                    loading={false}
                    readOnly={true}
                />
            </div>

            {onDelete && (
                <div className="batch-actions">
                    <button
                        className="delete-button"
                        onClick={handleDelete}
                        disabled={deleting}
                    >
                        {deleting ? 'Deleting...' : '🗑️ Delete Batch'}
                    </button>
                </div>
            )}
        </div>
    );
};

export default BatchViewer;
