import { useState, useRef, useCallback } from 'react';
import { filesApi } from '../services/api';
import { TenderFile } from '../types';

// --- Types ---

export type UploadStatus = 'idle' | 'uploading' | 'paused' | 'cancelling' | 'complete';

export interface UploadFileEntry {
    id: string;
    file: File;
    status: 'pending' | 'uploading' | 'completed' | 'failed' | 'cancelled';
    error?: string;
    /** Byte-level progress for chunked uploads */
    bytesUploaded: number;
}

export interface UploadProgress {
    total: number;
    completed: number;
    failed: number;
    cancelled: number;
    /** Overall bytes for all files */
    totalBytes: number;
    uploadedBytes: number;
    status: UploadStatus;
    files: UploadFileEntry[];
    currentFileName: string;
    /** If bulk-job backend path is used */
    bulkJobId?: string;
}

// --- Constants ---

/** Files at or below this count use frontend-concurrent path */
const FRONTEND_CONCURRENCY_THRESHOLD = 20;
/** Number of concurrent upload workers for frontend path */
const CONCURRENCY = 5;
/** Max retries per file (frontend path) */
const MAX_RETRIES = 2;
/** Size threshold for chunked uploads (50 MB) */
const CHUNK_THRESHOLD = 50 * 1024 * 1024;
/** Chunk size (5 MB) */
const CHUNK_SIZE = 5 * 1024 * 1024;
/** Bulk endpoint batch size (files per request) */
const BULK_BATCH_SIZE = 20;
/** Polling interval for bulk job status (ms) */
const BULK_POLL_INTERVAL = 2000;

// --- Helper: generate a short unique id ---
let _idCounter = 0;
function nextId(): string {
    return `upload-${Date.now()}-${++_idCounter}`;
}

// --- Hook ---

export function useUploadManager(tenderId: string | undefined) {
    const [progress, setProgress] = useState<UploadProgress | null>(null);

    // Mutable refs for worker coordination (avoid stale closure issues)
    const queueRef = useRef<UploadFileEntry[]>([]);
    const activeControllersRef = useRef<Map<string, AbortController>>(new Map());
    const pausedRef = useRef(false);
    const cancelledRef = useRef(false);
    const progressRef = useRef<UploadProgress | null>(null);
    const bulkPollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Publish progress to React state (batched)
    const publishProgress = useCallback((updater: (prev: UploadProgress) => UploadProgress) => {
        const current = progressRef.current;
        if (!current) return;
        const next = updater(current);
        progressRef.current = next;
        setProgress({ ...next });
    }, []);

    // ---- Frontend concurrent path ----

    const uploadOneFile = useCallback(async (
        entry: UploadFileEntry,
        tid: string,
        retries: number = 0,
    ): Promise<void> => {
        if (cancelledRef.current) {
            publishProgress(p => {
                const f = p.files.find(f => f.id === entry.id);
                if (f) { f.status = 'cancelled'; }
                return { ...p, cancelled: p.cancelled + 1 };
            });
            return;
        }

        const controller = new AbortController();
        activeControllersRef.current.set(entry.id, controller);

        publishProgress(p => {
            const f = p.files.find(f => f.id === entry.id);
            if (f) { f.status = 'uploading'; }
            return { ...p, currentFileName: entry.file.name };
        });

        try {
            if (entry.file.size > CHUNK_THRESHOLD) {
                await chunkedUpload(entry, tid, controller.signal);
            } else {
                await filesApi.upload(tid, entry.file, 'uncategorized', undefined, controller.signal);
            }

            activeControllersRef.current.delete(entry.id);

            publishProgress(p => {
                const f = p.files.find(f => f.id === entry.id);
                if (f) {
                    f.status = 'completed';
                    f.bytesUploaded = entry.file.size;
                }
                return {
                    ...p,
                    completed: p.completed + 1,
                    uploadedBytes: p.uploadedBytes + entry.file.size,
                };
            });
        } catch (err: any) {
            activeControllersRef.current.delete(entry.id);

            if (err?.name === 'CanceledError' || err?.name === 'AbortError' || controller.signal.aborted) {
                publishProgress(p => {
                    const f = p.files.find(f => f.id === entry.id);
                    if (f) { f.status = 'cancelled'; }
                    return { ...p, cancelled: p.cancelled + 1 };
                });
                return;
            }

            if (retries < MAX_RETRIES) {
                await new Promise(r => setTimeout(r, 1000 * (retries + 1)));
                return uploadOneFile(entry, tid, retries + 1);
            }

            publishProgress(p => {
                const f = p.files.find(f => f.id === entry.id);
                if (f) { f.status = 'failed'; f.error = String(err); }
                return { ...p, failed: p.failed + 1 };
            });
        }
    }, [publishProgress]);

    // Worker that pulls from queue
    const runWorker = useCallback(async (tid: string) => {
        while (queueRef.current.length > 0) {
            // Spin-wait while paused
            while (pausedRef.current && !cancelledRef.current) {
                await new Promise(r => setTimeout(r, 200));
            }
            if (cancelledRef.current) break;

            const entry = queueRef.current.shift();
            if (!entry) break;

            await uploadOneFile(entry, tid);
        }
    }, [uploadOneFile]);

    // ---- Chunked upload for large files ----

    const chunkedUpload = useCallback(async (
        entry: UploadFileEntry,
        tid: string,
        signal: AbortSignal,
    ) => {
        // 1. Init
        const initRes = await filesApi.initChunkedUpload(tid, {
            filename: entry.file.name,
            size: entry.file.size,
            category: 'uncategorized',
            content_type: entry.file.type || 'application/octet-stream',
        }, signal);

        const { upload_id, total_chunks, chunk_size } = initRes;
        const actualChunkSize = chunk_size || CHUNK_SIZE;

        // 2. Upload chunks with limited concurrency (3)
        const chunkIndexes = Array.from({ length: total_chunks }, (_, i) => i);
        const chunkQueue = [...chunkIndexes];
        let uploadedBytes = 0;

        const chunkWorker = async () => {
            while (chunkQueue.length > 0) {
                if (signal.aborted) return;
                const idx = chunkQueue.shift();
                if (idx === undefined) return;

                const start = idx * actualChunkSize;
                const end = Math.min(start + actualChunkSize, entry.file.size);
                const blob = entry.file.slice(start, end);

                await filesApi.uploadChunk(tid, upload_id, idx, blob, signal);
                uploadedBytes += (end - start);
                publishProgress(p => {
                    const f = p.files.find(f => f.id === entry.id);
                    if (f) { f.bytesUploaded = uploadedBytes; }
                    return { ...p };
                });
            }
        };

        const workers = Array.from({ length: 3 }, () => chunkWorker());
        await Promise.all(workers);

        // 3. Complete
        await filesApi.completeChunkedUpload(tid, upload_id, signal);
    }, [publishProgress]);

    // ---- Bulk (backend job) path ----

    const startBulkPath = useCallback(async (entries: UploadFileEntry[], tid: string) => {
        // Split entries into batches of BULK_BATCH_SIZE
        const batches: UploadFileEntry[][] = [];
        for (let i = 0; i < entries.length; i += BULK_BATCH_SIZE) {
            batches.push(entries.slice(i, i + BULK_BATCH_SIZE));
        }

        // Track cumulative counts across sequential batches
        let completedOffset = 0;
        let failedOffset = 0;

        // Upload batches sequentially (each is a single multi-file request)
        for (const batch of batches) {
            if (cancelledRef.current) break;

            const files = batch.map(e => e.file);
            try {
                const result = await filesApi.bulkUpload(tid, files, 'uncategorized');
                const jobId = result.job_id;

                publishProgress(p => ({ ...p, bulkJobId: jobId }));

                // Poll until this batch job completes
                await pollBulkJob(tid, jobId, batch, completedOffset, failedOffset);

                // Accumulate offsets from the completed batch
                const snap = progressRef.current;
                if (snap) {
                    completedOffset = snap.completed;
                    failedOffset = snap.failed;
                }
            } catch (err: any) {
                // Mark all files in this batch as failed
                for (const entry of batch) {
                    failedOffset++;
                    publishProgress(p => {
                        const f = p.files.find(f => f.id === entry.id);
                        if (f) { f.status = 'failed'; f.error = String(err); }
                        return { ...p, failed: failedOffset };
                    });
                }
            }
        }

        publishProgress(p => ({ ...p, status: 'complete', currentFileName: '' }));
    }, [publishProgress]);

    const pollBulkJob = useCallback(async (
        tid: string,
        jobId: string,
        batchEntries: UploadFileEntry[],
        completedOffset: number,
        failedOffset: number,
    ): Promise<void> => {
        return new Promise((resolve, reject) => {
            const poll = async () => {
                try {
                    if (cancelledRef.current) {
                        // Request cancel on backend
                        try { await filesApi.cancelBulkJob(tid, jobId); } catch { /* ignore */ }
                        // Mark remaining as cancelled
                        for (const entry of batchEntries) {
                            publishProgress(p => {
                                const f = p.files.find(f => f.id === entry.id);
                                if (f && f.status !== 'completed' && f.status !== 'failed') {
                                    f.status = 'cancelled';
                                }
                                return { ...p, cancelled: p.cancelled + 1 };
                            });
                        }
                        if (bulkPollTimerRef.current) clearInterval(bulkPollTimerRef.current);
                        resolve();
                        return;
                    }

                    const status = await filesApi.getBulkJobStatus(tid, jobId);

                    // Update progress with cumulative counts (offset from prior batches + current batch)
                    const cumulativeCompleted = completedOffset + status.success_count;
                    const cumulativeFailed = failedOffset + status.error_count;
                    publishProgress(p => {
                        // Estimate uploaded bytes proportionally
                        const processed = cumulativeCompleted + cumulativeFailed;
                        const estimatedBytes = p.totalBytes > 0 && p.total > 0
                            ? Math.round((processed / p.total) * p.totalBytes)
                            : 0;
                        return {
                            ...p,
                            completed: cumulativeCompleted,
                            failed: cumulativeFailed,
                            uploadedBytes: estimatedBytes,
                            currentFileName: status.current_file || '',
                        };
                    });

                    if (status.status === 'completed' || status.status === 'completed_with_errors' || status.status === 'failed' || status.status === 'cancelled') {
                        if (bulkPollTimerRef.current) clearInterval(bulkPollTimerRef.current);

                        // Map final statuses to entries
                        const failedNames = new Set(status.errors?.map((e: string) => e.split(':')[0].trim()) || []);
                        for (const entry of batchEntries) {
                            publishProgress(p => {
                                const f = p.files.find(f => f.id === entry.id);
                                if (f && f.status !== 'completed' && f.status !== 'failed' && f.status !== 'cancelled') {
                                    f.status = failedNames.has(entry.file.name) ? 'failed' : 'completed';
                                }
                                return { ...p };
                            });
                        }

                        resolve();
                        return;
                    }
                } catch (err) {
                    // Polling error — keep trying unless cancelled
                    if (cancelledRef.current) {
                        if (bulkPollTimerRef.current) clearInterval(bulkPollTimerRef.current);
                        resolve();
                    }
                }
            };

            bulkPollTimerRef.current = setInterval(poll, BULK_POLL_INTERVAL);
            poll(); // immediate first poll
        });
    }, [publishProgress]);

    // ---- Public API ----

    const startUpload = useCallback((files: File[]) => {
        if (!tenderId || files.length === 0) return;

        // Reset state
        cancelledRef.current = false;
        pausedRef.current = false;

        const entries: UploadFileEntry[] = files.map(file => ({
            id: nextId(),
            file,
            status: 'pending' as const,
            bytesUploaded: 0,
        }));

        const totalBytes = files.reduce((sum, f) => sum + f.size, 0);

        const initial: UploadProgress = {
            total: files.length,
            completed: 0,
            failed: 0,
            cancelled: 0,
            totalBytes,
            uploadedBytes: 0,
            status: 'uploading',
            files: entries,
            currentFileName: '',
        };

        progressRef.current = initial;
        setProgress({ ...initial });

        if (files.length <= FRONTEND_CONCURRENCY_THRESHOLD) {
            // Frontend concurrent path
            queueRef.current = [...entries];
            const workers = Array.from({ length: Math.min(CONCURRENCY, files.length) }, () => runWorker(tenderId!));
            Promise.all(workers).then(() => {
                publishProgress(p => ({ ...p, status: 'complete', currentFileName: '' }));
            });
        } else {
            // Bulk backend path
            startBulkPath(entries, tenderId!);
        }
    }, [tenderId, runWorker, startBulkPath, publishProgress]);

    const pause = useCallback(() => {
        pausedRef.current = true;
        publishProgress(p => ({ ...p, status: 'paused' }));
    }, [publishProgress]);

    const resume = useCallback(() => {
        pausedRef.current = false;
        publishProgress(p => ({ ...p, status: 'uploading' }));
    }, [publishProgress]);

    const cancel = useCallback(() => {
        cancelledRef.current = true;
        publishProgress(p => ({ ...p, status: 'cancelling' }));

        // Abort all active frontend requests
        activeControllersRef.current.forEach((controller) => {
            controller.abort();
        });
        activeControllersRef.current.clear();
        queueRef.current = [];

        // Poll timer cleanup
        if (bulkPollTimerRef.current) {
            clearInterval(bulkPollTimerRef.current);
            bulkPollTimerRef.current = null;
        }
    }, [publishProgress]);

    const dismiss = useCallback(() => {
        progressRef.current = null;
        setProgress(null);
        cancelledRef.current = false;
        pausedRef.current = false;
        queueRef.current = [];
        activeControllersRef.current.clear();
    }, []);

    return {
        progress,
        startUpload,
        pause,
        resume,
        cancel,
        dismiss,
    };
}
