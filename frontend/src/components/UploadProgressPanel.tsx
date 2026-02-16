import React from 'react';
import { UploadProgress, UploadStatus } from '../hooks/useUploadManager';
import './UploadProgressPanel.css';

interface UploadProgressPanelProps {
  progress: UploadProgress;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  onDismiss: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function statusLabel(status: UploadStatus, progress: UploadProgress): string {
  switch (status) {
    case 'uploading':
      return `Uploading ${progress.completed + progress.failed}/${progress.total}...`;
    case 'paused':
      return `Paused — ${progress.completed} completed, ${progress.total - progress.completed - progress.failed - progress.cancelled} remaining`;
    case 'cancelling':
      return 'Cancelling...';
    case 'complete': {
      if (progress.failed > 0 && progress.cancelled > 0) {
        return `Done: ${progress.completed} uploaded, ${progress.failed} failed, ${progress.cancelled} cancelled`;
      }
      if (progress.failed > 0) {
        return `Done: ${progress.completed} uploaded, ${progress.failed} failed`;
      }
      if (progress.cancelled > 0) {
        return `Cancelled — ${progress.completed} uploaded before cancellation`;
      }
      return `All ${progress.completed} files uploaded successfully`;
    }
    default:
      return '';
  }
}

const UploadProgressPanel: React.FC<UploadProgressPanelProps> = ({
  progress,
  onPause,
  onResume,
  onCancel,
  onDismiss,
}) => {
  const processed = progress.completed + progress.failed + progress.cancelled;
  const pct = progress.total > 0 ? Math.round((processed / progress.total) * 100) : 0;
  const isActive = progress.status === 'uploading' || progress.status === 'paused' || progress.status === 'cancelling';
  const isDone = progress.status === 'complete';

  // Determine bar color
  const barClass =
    progress.failed > 0 && isDone
      ? 'progress-fill progress-fill--warning'
      : progress.cancelled > 0 && isDone
        ? 'progress-fill progress-fill--cancelled'
        : 'progress-fill';

  return (
    <div className={`upload-progress-panel ${isDone ? 'upload-progress-panel--done' : ''}`}>
      <div className="upload-progress-header">
        <span className="upload-progress-label">
          {statusLabel(progress.status, progress)}
        </span>
        <span className="upload-progress-pct">{pct}%</span>
      </div>

      <div className="upload-progress-track">
        <div
          className={barClass}
          style={{ width: `${pct}%` }}
        />
      </div>

      {progress.currentFileName && isActive && (
        <div className="upload-progress-current">
          Current: {progress.currentFileName}
        </div>
      )}

      {progress.totalBytes > 0 && (
        <div className="upload-progress-bytes">
          {formatBytes(progress.uploadedBytes)} / {formatBytes(progress.totalBytes)}
        </div>
      )}

      {/* Failed files summary */}
      {isDone && progress.failed > 0 && (
        <div className="upload-progress-errors">
          <details>
            <summary>{progress.failed} file(s) failed</summary>
            <ul>
              {progress.files
                .filter(f => f.status === 'failed')
                .slice(0, 20)
                .map(f => (
                  <li key={f.id}>
                    <span className="error-filename">{f.file.name}</span>
                    {f.error && <span className="error-msg">— {f.error}</span>}
                  </li>
                ))}
              {progress.files.filter(f => f.status === 'failed').length > 20 && (
                <li className="error-more">
                  ...and {progress.files.filter(f => f.status === 'failed').length - 20} more
                </li>
              )}
            </ul>
          </details>
        </div>
      )}

      <div className="upload-progress-actions">
        {progress.status === 'uploading' && (
          <>
            <button className="btn-sm btn-secondary" onClick={onPause}>
              Pause
            </button>
            <button className="btn-sm btn-danger" onClick={onCancel}>
              Cancel
            </button>
          </>
        )}
        {progress.status === 'paused' && (
          <>
            <button className="btn-sm btn-primary" onClick={onResume}>
              Resume
            </button>
            <button className="btn-sm btn-danger" onClick={onCancel}>
              Cancel
            </button>
          </>
        )}
        {isDone && (
          <button className="btn-sm btn-secondary" onClick={onDismiss}>
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
};

export default UploadProgressPanel;
