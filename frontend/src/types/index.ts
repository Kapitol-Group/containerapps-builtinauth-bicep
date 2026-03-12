// Types for the application

export interface Tender {
    id: string;
    name: string;
    created_at: string;
    created_by: string;
    file_count: number;
    tender_type?: 'sharepoint' | 'mfiles';
    mfiles_project_id?: string;
    mfiles_project_name?: string;
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

export interface FrontendConfig {
    entraClientId: string;
    entraTenantId: string;
    sharepointBaseUrl: string;
    isMfilesDefaultsAdmin: boolean;
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
    source?: 'local' | 'sharepoint' | 'mfiles';
    batch_id?: string;
}

export type MFilesSearchModifier =
    | '<'
    | 'lt'
    | 'lte'
    | '>'
    | 'gt'
    | 'gte'
    | 'contains'
    | 'startswith'
    | 'equals'
    | '='
    | 'wild'
    | 'quick';

export interface MFilesSearchField {
    id: number;
    name: string;
    required: boolean;
    data_type?: number;
    data_type_word?: string;
    system_auto_fill?: boolean;
    automation_managed?: boolean;
    queue_required?: boolean;
    queue_default?: MFilesQueueDefault;
}

export type MFilesQueueDefaultRuleType = 'current_user' | 'fixed_text' | 'fixed_lookup';

export interface MFilesQueueDefault {
    id: string;
    document_class: string;
    property_name: string;
    rule_type: MFilesQueueDefaultRuleType;
    text_value?: string;
    lookup_value_id?: string;
    lookup_value_name?: string;
}

export interface MFilesQueueDefaultRule extends MFilesQueueDefault {
    enabled: boolean;
}

export interface MFilesQueueDefaultsResponse {
    rules: MFilesQueueDefaultRule[];
    updated_at: string;
}

export interface MFilesDocumentClass {
    id: string;
    name: string;
}

export interface MFilesPropertyValue {
    id: string;
    name: string;
}

export interface MFilesSearchCriterion {
    name: string;
    value: string;
    modifier: MFilesSearchModifier;
}

export interface MFilesSearchResult {
    title: string;
    display_id: string;
    score: number | null;
    single_file: boolean;
    last_modified?: string;
    file_count: number;
    file_names: string[];
    primary_filename?: string;
    file_type?: string;
}

export interface MFilesSearchResponse {
    criteria: MFilesSearchCriterion[];
    results: MFilesSearchResult[];
}

export interface MFilesImportDocument {
    display_id: string;
    title?: string;
    filename?: string;
}

export interface MFilesExtractionProperty {
    property_id: number;
    property_name: string;
    data_type?: number;
    data_type_word?: string;
    value?: string;
    value_id?: string;
    values?: string[];
    value_ids?: string[];
}

export interface ImportJobStatus {
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
    mfiles_document_class?: string;
    mfiles_properties?: MFilesExtractionProperty[];
    file_paths: string[];
    title_block_coords: TitleBlockCoords;
    status: 'pending' | 'submitting' | 'running' | 'completed' | 'failed';
    submitted_at: string;
    submitted_by: string;
    file_count: number;
    job_id?: string;
    // Enhanced tracking fields for retry/failure handling
    submission_attempts?: Array<{
        timestamp: string;
        started_at?: string;
        completed_at?: string;
        duration_seconds?: number;
        status: string;
        source?: string;
        reference?: string;
        error?: string;
    }>;
    last_error?: string;
    completed_at?: string;
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

export type BatchMetricSource = 'exact' | 'estimated' | 'unavailable';

export interface BatchProgressFile {
    filename: string;
    status: 'queued' | 'extracted' | 'failed' | 'exported';
    drawing_number: string | null;
    drawing_revision: string | null;
    drawing_title: string | null;
    destination_path: string | null;
    created_at: string | null;
    updated_at: string | null;
}

export interface BatchSubmissionMetric {
    duration_seconds: number | null;
    attempt_count: number;
    source: BatchMetricSource;
}

export interface BatchDurationMetric {
    started_at: string | null;
    ended_at: string | null;
    duration_seconds: number | null;
    source: BatchMetricSource;
}

export interface BatchCompletionMetric {
    completed_at: string | null;
    source: BatchMetricSource;
}

export interface BatchThroughputMetric {
    processed_files: number;
    files_per_minute: number | null;
    source: BatchMetricSource;
}

export interface BatchProgressMetrics {
    submission: BatchSubmissionMetric;
    extraction: BatchDurationMetric;
    completion: BatchCompletionMetric;
    total: BatchDurationMetric;
    throughput: BatchThroughputMetric;
}

export interface BatchProgressResponse {
    batch_id: string;
    total_files: number;
    status_counts: BatchStatusCounts;
    files: BatchProgressFile[];
    metrics: BatchProgressMetrics;
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
