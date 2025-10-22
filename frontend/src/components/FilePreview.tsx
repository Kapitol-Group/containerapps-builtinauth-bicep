import React from 'react';
import { TenderFile } from '../types';

interface FilePreviewProps {
  file: TenderFile | null;
}

const FilePreview: React.FC<FilePreviewProps> = ({ file }) => {
  if (!file) {
    return <div className="file-preview"><p>Select a file to preview</p></div>;
  }

  return (
    <div className="file-preview">
      <h3>{file.name}</h3>
      <p>Preview for {file.content_type}</p>
      <p className="placeholder">PDF/Office preview integration coming soon</p>
    </div>
  );
};

export default FilePreview;
