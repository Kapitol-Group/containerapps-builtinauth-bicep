import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import './FileUploadZone.css';

interface FileUploadZoneProps {
  onFilesDropped: (files: File[]) => void;
}

const FileUploadZone: React.FC<FileUploadZoneProps> = ({ onFilesDropped }) => {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    onFilesDropped(acceptedFiles);
  }, [onFilesDropped]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true
  });

  return (
    <div {...getRootProps()} className={`upload-zone ${isDragActive ? 'active' : ''}`}>
      <input {...getInputProps()} />
      <div className="upload-content">
        {isDragActive ? (
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
