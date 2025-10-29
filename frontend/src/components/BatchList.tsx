import React from 'react';
import { Batch } from '../types';
import './BatchList.css';

interface BatchListProps {
    batches: Batch[];
    selectedBatchId: string | null;
    onBatchSelect: (batchId: string) => void;
    loading?: boolean;
}

const BatchList: React.FC<BatchListProps> = ({
    batches,
    selectedBatchId,
    onBatchSelect,
    loading = false,
}) => {
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
                    </div>
                </div>
            ))}
        </div>
    );
};

export default BatchList;
