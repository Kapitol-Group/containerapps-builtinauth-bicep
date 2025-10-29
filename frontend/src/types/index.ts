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
    discipline: string;
    file_paths: string[];
    title_block_coords: TitleBlockCoords;
    status: 'pending' | 'running' | 'completed' | 'failed';
    submitted_at: string;
    submitted_by: string;
    file_count: number;
    job_id?: string;
}

export interface BatchWithFiles {
    batch: Batch;
    files: TenderFile[];
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
