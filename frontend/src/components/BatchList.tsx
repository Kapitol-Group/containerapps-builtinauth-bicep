import React, { useEffect, useRef, useState } from 'react';
import { Batch, BatchProgressSummary } from '../types';
import { batchesApi } from '../services/api';
import './BatchList.css';

interface BatchListProps {
    batches: Batch[];
    selectedBatchId: string | null;
    onBatchSelect: (batchId: string) => void;
    loading?: boolean;
    tenderId: string;
    onReload: () => void;
}

const BatchList: React.FC<BatchListProps> = ({
    batches,
    selectedBatchId,
    onBatchSelect,
    loading = false,
    tenderId,
    onReload,
}) => {
    const [batchProgress, setBatchProgress] = useState<Record<string, BatchProgressSummary>>({});
    const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const pollInFlightRef = useRef(false);
    const onReloadRef = useRef(onReload);
    onReloadRef.current = onReload;
    
    // Get polling interval from environment or default to 30 seconds
    const pollingInterval = parseInt(
        (window as any).BATCH_PROGRESS_POLLING_INTERVAL || '30000',
        10
    );

    // Poll for progress on running batches
    useEffect(() => {
        const runningBatchIds = batches
            .filter(batch => batch.status === 'running')
            .map(batch => batch.batch_id);

        if (runningBatchIds.length === 0) {
            // Clear polling if no running batches
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
            }
            pollInFlightRef.current = false;
            return;
        }

        let isCancelled = false;

        const pollProgress = async () => {
            if (isCancelled || pollInFlightRef.current) {
                return;
            }

            pollInFlightRef.current = true;
            try {
                const summary = await batchesApi.getProgressSummary(tenderId, runningBatchIds);
                if (isCancelled) {
                    return;
                }

                const progressByBatch = summary.progress_by_batch || {};
                if (Object.keys(progressByBatch).length > 0) {
                    setBatchProgress(prev => ({
                        ...prev,
                        ...progressByBatch,
                    }));
                }

                let shouldReload = false;
                for (const batchId of runningBatchIds) {
                    const progress = progressByBatch[batchId];
                    if (!progress) {
                        continue;
                    }

                    const { queued, extracted } = progress.status_counts;
                    if (queued === 0 && extracted === 0) {
                        shouldReload = true;
                        break;
                    }
                }

                if (shouldReload) {
                    onReloadRef.current();
                }

                if (summary.errors_by_batch) {
                    for (const [batchId, message] of Object.entries(summary.errors_by_batch)) {
                        console.error(`Failed to poll progress summary for batch ${batchId}: ${message}`);
                    }
                }
            } catch (error) {
                console.error('Failed to poll batch progress summary:', error);
            } finally {
                pollInFlightRef.current = false;
            }
        };

        // Initial poll
        pollProgress();

        // Set up interval
        if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
        }
        pollingIntervalRef.current = setInterval(pollProgress, pollingInterval);

        // Cleanup on unmount or when dependencies change
        return () => {
            isCancelled = true;
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
            }
            pollInFlightRef.current = false;
        };
    }, [batches, tenderId, pollingInterval]);

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

    const formatDate = (dateString: string) => {
        try {
            const date = new Date(dateString);
            return date.toLocaleString();
        } catch {
            return dateString;
        }
    };

    if (loading) {
        return (
            <div className="batch-list-loading">
                <p>Loading batches...</p>
            </div>
        );
    }

    if (batches.length === 0) {
        return (
            <div className="batch-list-empty">
                <p>No batches submitted yet</p>
                <p className="empty-hint">
                    Select files and queue extraction to create a batch
                </p>
            </div>
        );
    }

    const renderProgressBar = (batch: Batch) => {
        const progress = batchProgress[batch.batch_id];
        if (!progress || batch.status !== 'running') {
            return null;
        }

        const { exported, failed, extracted, queued } = progress.status_counts;
        const total = progress.total_files;
        const processed = exported + failed;
        const percentComplete = total > 0 ? Math.round((processed / total) * 100) : 0;
        const exportedPercent = total > 0 ? (exported / total) * 100 : 0;
        const failedPercent = total > 0 ? (failed / total) * 100 : 0;

        return (
            <div className="batch-progress">
                <div className="progress-bar">
                    <div 
                        className="progress-fill progress-exported"
                        style={{ width: `${exportedPercent}%` }}
                    />
                    <div 
                        className="progress-fill progress-failed"
                        style={{ width: `${failedPercent}%` }}
                    />
                </div>
                <div className="progress-stats">
                    <span className="progress-text">{processed} of {total} processed ({percentComplete}%)</span>
                    <div className="status-breakdown">
                        {exported > 0 && <span className="stat-exported">✓ {exported}</span>}
                        {extracted > 0 && <span className="stat-extracted">⏳ {extracted}</span>}
                        {failed > 0 && <span className="stat-failed">✗ {failed}</span>}
                        {queued > 0 && <span className="stat-queued">⋯ {queued}</span>}
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="batch-list">
            {batches.map((batch) => (
                <div
                    key={batch.batch_id}
                    className={`batch-card ${selectedBatchId === batch.batch_id ? 'selected' : ''}`}
                    onClick={() => onBatchSelect(batch.batch_id)}
                >
                    <div className="batch-card-header">
                        <h3 className="batch-name">{batch.batch_name}</h3>
                        <span className={`status-badge ${getStatusBadgeClass(batch.status)}`}>
                            {batch.status}
                        </span>
                    </div>
                    <div className="batch-card-body">
                        <div className="batch-info-row">
                            <span className="batch-info-label">Discipline:</span>
                            <span className="batch-info-value">{batch.discipline}</span>
                        </div>
                        <div className="batch-info-row">
                            <span className="batch-info-label">Files:</span>
                            <span className="batch-info-value">{batch.file_count}</span>
                        </div>
                        <div className="batch-info-row">
                            <span className="batch-info-label">Submitted:</span>
                            <span className="batch-info-value">{formatDate(batch.submitted_at)}</span>
                        </div>
                        <div className="batch-info-row">
                            <span className="batch-info-label">By:</span>
                            <span className="batch-info-value">{batch.submitted_by}</span>
                        </div>
                        {batch.job_id && (
                            <div className="batch-info-row">
                                <span className="batch-info-label">Job ID:</span>
                                <span className="batch-info-value batch-job-id">{batch.job_id}</span>
                            </div>
                        )}
                        {renderProgressBar(batch)}
                    </div>
                </div>
            ))}
        </div>
    );
};

export default BatchList;
