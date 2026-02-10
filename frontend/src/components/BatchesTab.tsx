import React, { useState, useEffect } from 'react';
import { batchesApi } from '../services/api';
import BatchList from './BatchList';
import BatchViewer from './BatchViewer';
import { Batch, TenderFile, BatchWithFiles } from '../types';
import './BatchesTab.css';

interface BatchesTabProps {
    tenderId: string;
    onError: (message: string) => void;
    onReloadFiles: () => void;
}

const BatchesTab: React.FC<BatchesTabProps> = ({ tenderId, onError, onReloadFiles }) => {
    const [batches, setBatches] = useState<Batch[]>([]);
    const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
    const [selectedBatchData, setSelectedBatchData] = useState<BatchWithFiles | null>(null);
    const [loading, setLoading] = useState(false);
    const [loadingBatch, setLoadingBatch] = useState(false);

    const loadBatches = async () => {
        try {
            setLoading(true);
            const fetchedBatches = await batchesApi.list(tenderId);
            setBatches(fetchedBatches);
        } catch (error) {
            console.error('Failed to load batches:', error);
            onError('Failed to load batches');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadBatches();
    }, [tenderId]);

    const handleBatchSelect = async (batchId: string) => {
        try {
            setLoadingBatch(true);
            setSelectedBatchId(batchId);
            const batchData = await batchesApi.get(tenderId, batchId);
            setSelectedBatchData(batchData);
        } catch (error: any) {
            console.error('Failed to load batch:', error);
            onError(error.message || 'Failed to load batch');
            setSelectedBatchId(null);
        } finally {
            setLoadingBatch(false);
        }
    };

    const handleBatchClose = () => {
        setSelectedBatchId(null);
        setSelectedBatchData(null);
        loadBatches(); // Reload batches when closing detail view
    };

    const handleFileSelect = (file: TenderFile) => {
        // Handle file selection if needed
        console.log('File selected:', file);
    };

    const handleBatchDelete = () => {
        // Optimistically remove the deleted batch so the list updates instantly
        if (selectedBatchId) {
            setBatches(prev => prev.filter(b => b.batch_id !== selectedBatchId));
        }
        // Clear selection to return to list view
        setSelectedBatchId(null);
        setSelectedBatchData(null);
        // Reload files since batch files are now uncategorized
        onReloadFiles();
        // Silently refresh batch list in background (no loading indicator)
        batchesApi.list(tenderId)
            .then(fetched => setBatches(fetched))
            .catch(() => {});
    };

    return (
        <div className="batches-tab">
            {!selectedBatchId ? (
                <BatchList
                    batches={batches}
                    selectedBatchId={selectedBatchId}
                    onBatchSelect={handleBatchSelect}
                    loading={loading}
                    tenderId={tenderId}
                    onReload={loadBatches}
                />
            ) : selectedBatchData ? (
                <BatchViewer
                    batch={selectedBatchData.batch}
                    files={selectedBatchData.files}
                    tenderId={tenderId}
                    onClose={handleBatchClose}
                    onFileSelect={handleFileSelect}
                    loading={loadingBatch}
                    onDelete={handleBatchDelete}
                />
            ) : (
                <div className="loading-message">Loading batch...</div>
            )}
        </div>
    );
};

export default BatchesTab;
