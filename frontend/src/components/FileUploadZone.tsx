import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import './FileUploadZone.css';

interface FileUploadZoneProps {
  onFilesDropped: (files: File[]) => void;
  disabled?: boolean;
}

const FileUploadZone: React.FC<FileUploadZoneProps> = ({ onFilesDropped, disabled = false }) => {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (!disabled) {
      onFilesDropped(acceptedFiles);
    }
  }, [onFilesDropped, disabled]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    disabled,
  });

  return (
    <div {...getRootProps()} className={`upload-zone ${isDragActive ? 'active' : ''} ${disabled ? 'disabled' : ''}`}>
      <input {...getInputProps()} />
      <div className="upload-content">
        {disabled ? (
          <p>Upload in progress...</p>
        ) : isDragActive ? (
          <p>Drop files here...</p>
        ) : (
          <>
            <p>Drag & drop files here, or click to select files</p>
            <button className="btn-secondary">Select Files</button>
          </>
        )}
      </div>
    </div>
  );
};

export default FileUploadZone;
