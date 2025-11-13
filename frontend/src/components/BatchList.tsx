import React, { useEffect, useRef, useState } from 'react';
import { Batch } from '../types';
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

interface BatchProgress {
    batch_id: string;
    total_files: number;
    status_counts: {
        queued: number;
        extracted: number;
        failed: number;
        exported: number;
    };
}

const BatchList: React.FC<BatchListProps> = ({
    batches,
    selectedBatchId,
    onBatchSelect,
    loading = false,
    tenderId,
    onReload,
}) => {
    const [batchProgress, setBatchProgress] = useState<Record<string, BatchProgress>>({});
    const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
    
    // Get polling interval from environment or default to 30 seconds
    const pollingInterval = parseInt(
        (window as any).BATCH_PROGRESS_POLLING_INTERVAL || '30000',
        10
    );

    // Poll for progress on running batches
    useEffect(() => {
        const runningBatches = batches.filter(b => b.status === 'running');
        
        if (runningBatches.length === 0) {
            // Clear polling if no running batches
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
            }
            return;
        }

        const pollProgress = async () => {
            for (const batch of runningBatches) {
                try {
                    const progress = await batchesApi.getProgress(tenderId, batch.batch_id);
                    
                    setBatchProgress(prev => ({
                        ...prev,
                        [batch.batch_id]: progress
                    }));

                    // Check if batch is complete (all files in terminal states)
                    const { queued, extracted } = progress.status_counts;
                    if (queued === 0 && extracted === 0) {
                        // Batch is complete, reload list to update status
                        onReload();
                    }
                } catch (error) {
                    console.error(`Failed to poll progress for batch ${batch.batch_id}:`, error);
                }
            }
        };

        // Initial poll
        pollProgress();

        // Set up interval
        pollingIntervalRef.current = setInterval(pollProgress, pollingInterval);

        // Cleanup on unmount or when dependencies change
        return () => {
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
            }
        };
    }, [batches, tenderId, pollingInterval, onReload]);

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

        return (
            <div className="batch-progress">
                <div className="progress-bar">
                    <div 
                        className="progress-fill progress-exported"
                        style={{ width: `${(exported / total) * 100}%` }}
                    />
                    <div 
                        className="progress-fill progress-failed"
                        style={{ width: `${(failed / total) * 100}%` }}
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
