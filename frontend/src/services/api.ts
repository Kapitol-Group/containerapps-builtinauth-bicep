import axios from 'axios';
import { Tender, TenderFile, ExtractionJob, ApiResponse, TitleBlockCoords, Batch, BatchWithFiles } from '../types';

const API_BASE_URL = import.meta.env.VITE_BACKEND_API_URL || '/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Config API
export const configApi = {
    get: async (): Promise<{ entraClientId: string; entraTenantId: string; sharepointBaseUrl: string }> => {
        const response = await api.get<ApiResponse<{ entraClientId: string; entraTenantId: string; sharepointBaseUrl: string }>>('/config');
        if (!response.data.success || !response.data.data) {
            throw new Error('Failed to fetch configuration');
        }
        return response.data.data;
    },
};

// Tenders API
export const tendersApi = {
    list: async (): Promise<Tender[]> => {
        const response = await api.get<ApiResponse<Tender[]>>('/tenders');
        return response.data.data || [];
    },

    create: async (data: {
        name: string;
        sharepoint_path?: string;
        output_location?: string;
        sharepoint_site_id?: string;
        sharepoint_library_id?: string;
        sharepoint_folder_path?: string;
        output_site_id?: string;
        output_library_id?: string;
        output_folder_path?: string;
    }): Promise<Tender> => {
        const response = await api.post<ApiResponse<Tender>>('/tenders', data);
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to create tender');
        }
        return response.data.data;
    },

    get: async (tenderId: string): Promise<Tender> => {
        const response = await api.get<ApiResponse<Tender>>(`/tenders/${tenderId}`);
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to fetch tender');
        }
        return response.data.data;
    },

    delete: async (tenderId: string): Promise<void> => {
        await api.delete(`/tenders/${tenderId}`);
    },
};

// Files API
export const filesApi = {
    list: async (tenderId: string, excludeBatched: boolean = false): Promise<TenderFile[]> => {
        const params = excludeBatched ? { exclude_batched: 'true' } : {};
        const response = await api.get<ApiResponse<TenderFile[]>>(`/tenders/${tenderId}/files`, { params });
        return response.data.data || [];
    },

    upload: async (tenderId: string, file: File, category: string = 'uncategorized', source?: 'local' | 'sharepoint', signal?: AbortSignal): Promise<TenderFile> => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', category);
        if (source) {
            formData.append('source', source);
        }

        const response = await api.post<ApiResponse<TenderFile>>(
            `/tenders/${tenderId}/files`,
            formData,
            {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
                timeout: 120000, // 120s per file
                signal,
            }
        );

        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to upload file');
        }
        return response.data.data;
    },

    download: async (tenderId: string, filePath: string): Promise<Blob> => {
        const response = await api.get(`/tenders/${tenderId}/files/${filePath}`, {
            responseType: 'blob',
        });
        return response.data;
    },

    updateCategory: async (tenderId: string, filePath: string, category: string): Promise<void> => {
        await api.put(`/tenders/${tenderId}/files/${filePath}/category`, { category });
    },

    delete: async (tenderId: string, filePath: string): Promise<void> => {
        await api.delete(`/tenders/${tenderId}/files/${filePath}`);
    },

    // --- Bulk upload (backend job) ---

    bulkUpload: async (tenderId: string, files: File[], category: string = 'uncategorized'): Promise<{ job_id: string; total_files: number }> => {
        const formData = new FormData();
        for (const file of files) {
            formData.append('files', file);
        }
        formData.append('category', category);

        const response = await api.post<ApiResponse<{ job_id: string; total_files: number }>>(
            `/tenders/${tenderId}/files/bulk`,
            formData,
            {
                headers: { 'Content-Type': 'multipart/form-data' },
                timeout: 300000, // 5 min to send all files
            }
        );
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to start bulk upload');
        }
        return response.data.data;
    },

    getBulkJobStatus: async (tenderId: string, jobId: string): Promise<{
        job_id: string;
        status: string;
        progress: number;
        total: number;
        current_file: string;
        success_count: number;
        error_count: number;
        errors: string[];
    }> => {
        const response = await api.get<ApiResponse<any>>(`/tenders/${tenderId}/files/bulk-jobs/${jobId}`);
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to get bulk job status');
        }
        return response.data.data;
    },

    cancelBulkJob: async (tenderId: string, jobId: string): Promise<void> => {
        await api.post(`/tenders/${tenderId}/files/bulk-jobs/${jobId}/cancel`);
    },

    // --- Chunked upload ---

    initChunkedUpload: async (tenderId: string, params: {
        filename: string;
        size: number;
        category: string;
        content_type: string;
    }, signal?: AbortSignal): Promise<{ upload_id: string; chunk_size: number; total_chunks: number }> => {
        const response = await api.post<ApiResponse<{ upload_id: string; chunk_size: number; total_chunks: number }>>(
            `/tenders/${tenderId}/uploads/init`,
            params,
            { signal }
        );
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to init chunked upload');
        }
        return response.data.data;
    },

    uploadChunk: async (tenderId: string, uploadId: string, chunkIndex: number, data: Blob, signal?: AbortSignal): Promise<void> => {
        await api.put(
            `/tenders/${tenderId}/uploads/${uploadId}/chunks/${chunkIndex}`,
            data,
            {
                headers: { 'Content-Type': 'application/octet-stream' },
                timeout: 120000,
                signal,
            }
        );
    },

    completeChunkedUpload: async (tenderId: string, uploadId: string, signal?: AbortSignal): Promise<TenderFile> => {
        const response = await api.post<ApiResponse<TenderFile>>(
            `/tenders/${tenderId}/uploads/${uploadId}/complete`,
            {},
            { signal }
        );
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to complete chunked upload');
        }
        return response.data.data;
    },

    getChunkedUploadStatus: async (tenderId: string, uploadId: string): Promise<{ completed_chunks: number[]; total_chunks: number }> => {
        const response = await api.get<ApiResponse<{ completed_chunks: number[]; total_chunks: number }>>(
            `/tenders/${tenderId}/uploads/${uploadId}/status`
        );
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to get chunked upload status');
        }
        return response.data.data;
    },
};

// UiPath API
export const uipathApi = {
    queueExtraction: async (
        tenderId: string,
        tenderName: string,
        filePaths: string[],
        discipline: string,
        titleBlockCoords: TitleBlockCoords,
        batchName?: string,
        sharepointFolderPath?: string,
        outputFolderPath?: string,
        folderList?: string[]
    ): Promise<{ batch_id: string; job_id: string; status: string; batch: Batch }> => {
        const response = await api.post<ApiResponse<{ batch_id: string; job_id: string; status: string; batch: Batch }>>('/uipath/extract', {
            tender_id: tenderId,
            tender_name: tenderName,
            file_paths: filePaths,
            discipline,
            title_block_coords: titleBlockCoords,
            batch_name: batchName,
            sharepoint_folder_path: sharepointFolderPath,
            output_folder_path: outputFolderPath,
            folder_list: folderList,
        });

        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to queue extraction job');
        }
        return response.data.data;
    },

    getJobStatus: async (jobId: string): Promise<ExtractionJob> => {
        const response = await api.get<ApiResponse<ExtractionJob>>(`/uipath/jobs/${jobId}`);
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to fetch job status');
        }
        return response.data.data;
    },
};

// Batches API
export const batchesApi = {
    list: async (tenderId: string): Promise<Batch[]> => {
        const response = await api.get<ApiResponse<Batch[]>>(`/tenders/${tenderId}/batches`);
        return response.data.data || [];
    },

    get: async (tenderId: string, batchId: string): Promise<BatchWithFiles> => {
        const response = await api.get<ApiResponse<BatchWithFiles>>(`/tenders/${tenderId}/batches/${batchId}`);
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to fetch batch');
        }
        return response.data.data;
    },

    getProgress: async (tenderId: string, batchId: string): Promise<{
        batch_id: string;
        total_files: number;
        status_counts: {
            queued: number;
            extracted: number;
            failed: number;
            exported: number;
        };
        files: Array<{
            filename: string;
            status: 'queued' | 'extracted' | 'failed' | 'exported';
            drawing_number: string | null;
            drawing_revision: string | null;
            drawing_title: string | null;
            destination_path: string | null;
            created_at: string | null;
            updated_at: string | null;
        }>;
    }> => {
        const response = await api.get<ApiResponse<any>>(`/tenders/${tenderId}/batches/${batchId}/progress`);
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to fetch batch progress');
        }
        return response.data.data;
    },

    retry: async (tenderId: string, batchId: string): Promise<void> => {
        const response = await api.post<ApiResponse<{ message: string }>>(`/tenders/${tenderId}/batches/${batchId}/retry`);
        if (!response.data.success) {
            throw new Error(response.data.error || 'Failed to retry batch');
        }
    },

    updateStatus: async (tenderId: string, batchId: string, status: 'pending' | 'running' | 'completed' | 'failed'): Promise<Batch> => {
        const response = await api.patch<ApiResponse<Batch>>(`/tenders/${tenderId}/batches/${batchId}`, { status });
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to update batch status');
        }
        return response.data.data;
    },

    delete: async (tenderId: string, batchId: string): Promise<void> => {
        await api.delete(`/tenders/${tenderId}/batches/${batchId}`);
    },
};

// SharePoint API
export const sharepointApi = {
    validatePath: async (path: string): Promise<boolean> => {
        const response = await api.post<ApiResponse<{ valid: boolean }>>('/sharepoint/validate', { path });
        return response.data.data?.valid || false;
    },

    listFolders: async (accessToken: string, driveId: string, folderPath: string): Promise<Array<{ name: string; id: string; path: string }>> => {
        const response = await api.post<ApiResponse<Array<{ name: string; id: string; path: string }>>>('/sharepoint/list-folders', {
            access_token: accessToken,
            drive_id: driveId,
            folder_path: folderPath
        });
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to list SharePoint folders');
        }
        return response.data.data;
    },

    importFiles: async (
        tenderId: string,
        accessToken: string,
        items: Array<{
            name: string;
            downloadUrl: string;
            driveId: string;
            itemId: string;
            relativePath?: string;
            size?: number;
            mimeType?: string;
        }>,
        category?: string
    ): Promise<{ job_id: string; status: string; total: number }> => {
        const response = await api.post<ApiResponse<{ job_id: string; status: string; total: number }>>('/sharepoint/import-files', {
            tender_id: tenderId,
            access_token: accessToken,
            items,
            category
        });
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to start SharePoint import');
        }
        return response.data.data;
    },

    getImportJobStatus: async (jobId: string): Promise<{
        job_id: string;
        tender_id: string;
        status: 'running' | 'completed' | 'completed_with_errors' | 'failed';
        progress: number;
        total: number;
        current_file: string;
        success_count: number;
        error_count: number;
        errors: string[];
        created_at: string;
        updated_at: string;
        completed_at?: string;
    }> => {
        const response = await api.get<ApiResponse<any>>(`/sharepoint/import-jobs/${jobId}`);
        if (!response.data.success || !response.data.data) {
            throw new Error(response.data.error || 'Failed to get import job status');
        }
        return response.data.data;
    },
};

// Health check
export const healthCheck = async (): Promise<boolean> => {
    try {
        const response = await api.get('/health');
        return response.status === 200;
    } catch {
        return false;
    }
};

export default api;
