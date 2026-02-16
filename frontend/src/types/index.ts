// Types for the application

export interface Tender {
    id: string;
    name: string;
    created_at: string;
    created_by: string;
    file_count: number;
    sharepoint_path?: string; // Deprecated - kept for backward compatibility
    output_location?: string; // Deprecated - kept for backward compatibility
    // New SharePoint identifiers
    sharepoint_site_id?: string;
    sharepoint_library_id?: string;
    sharepoint_folder_path?: string;
    // Output location identifiers
    output_site_id?: string;
    output_library_id?: string;
    output_folder_path?: string;
}

export interface TenderFile {
    name: string;
    path: string;
    size: number;
    content_type: string | null;
    category: string;
    uploaded_by: string | null;
    uploaded_at: string | null;
    last_modified: string | null;
    source?: 'local' | 'sharepoint';
    batch_id?: string;
}

export interface TitleBlockCoords {
    x: number;
    y: number;
    width: number;
    height: number;
}

export interface Batch {
    batch_id: string;
    batch_name: string;
    discipline?: string; // Legacy field, kept for backward compatibility
    destination?: string; // New field: SharePoint destination folder
    file_paths: string[];
    title_block_coords: TitleBlockCoords;
    status: 'pending' | 'running' | 'completed' | 'failed';
    submitted_at: string;
    submitted_by: string;
    file_count: number;
    job_id?: string;
    // Enhanced tracking fields for retry/failure handling
    submission_attempts?: Array<{
        timestamp: string;
        status: string;
        reference?: string;
        error?: string;
    }>;
    last_error?: string;
    uipath_reference?: string;
    uipath_submission_id?: string;
    uipath_project_id?: string;
}

export interface BatchWithFiles {
    batch: Batch;
    files: TenderFile[];
}

export interface BatchStatusCounts {
    queued: number;
    extracted: number;
    failed: number;
    exported: number;
}

export interface BatchProgressSummary {
    batch_id: string;
    total_files: number;
    status_counts: BatchStatusCounts;
}

export interface BatchProgressSummaryResponse {
    progress_by_batch: Record<string, BatchProgressSummary>;
    errors_by_batch?: Record<string, string>;
}

export interface ExtractionJob {
    job_id: string;
    status: string;
    tender_id: string;
    file_count?: number;
    submitted_at: string;
    submitted_by: string;
    message?: string;
    batch_id?: string;
}

export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
}
