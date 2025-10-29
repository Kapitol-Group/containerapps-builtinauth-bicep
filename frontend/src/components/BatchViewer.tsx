import React, { useState } from 'react';
import { Batch, TenderFile } from '../types';
import FileBrowser from './FileBrowser';
import './BatchViewer.css';

interface BatchViewerProps {
    batch: Batch;
    files: TenderFile[];
    onClose: () => void;
    onFileSelect: (file: TenderFile) => void;
    loading?: boolean;
}

const BatchViewer: React.FC<BatchViewerProps> = ({
    batch,
    files,
    onClose,
    onFileSelect,
    loading = false,
}) => {
    const [selectedFile, setSelectedFile] = useState<TenderFile | null>(null);

    const handleFileSelect = (file: TenderFile) => {
        setSelectedFile(file);
        onFileSelect(file);
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
                        <span className="metadata-item coords-item">
                            <strong>Title Block:</strong> X:{batch.title_block_coords.x} Y:{batch.title_block_coords.y} 
                            {' '}W:{batch.title_block_coords.width} H:{batch.title_block_coords.height}
                        </span>
                    </div>
                </div>
            </div>

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
