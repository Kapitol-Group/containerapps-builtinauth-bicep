// Types for the application

export interface Tender {
    id: string;
    name: string;
    created_at: string;
    created_by: string;
    file_count: number;
    sharepoint_path?: string;
    output_location?: string;
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
}

export interface TitleBlockCoords {
    x: number;
    y: number;
    width: number;
    height: number;
}

export interface ExtractionJob {
    job_id: string;
    status: string;
    tender_id: string;
    file_count?: number;
    submitted_at: string;
    submitted_by: string;
    message?: string;
}

export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
}
