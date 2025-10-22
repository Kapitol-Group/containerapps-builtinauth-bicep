import React from 'react';
import { TenderFile } from '../types';

interface FileBrowserProps {
  files: TenderFile[];
  selectedFile: TenderFile | null;
  selectedFiles: TenderFile[];
  onFileSelect: (file: TenderFile) => void;
  onSelectionChange: (files: TenderFile[]) => void;
  loading: boolean;
}

const FileBrowser: React.FC<FileBrowserProps> = ({ files, selectedFile, onFileSelect, loading }) => {
  return (
    <div className="file-browser">
      <h3>Files</h3>
      {loading ? <p>Loading...</p> : (
        <div className="file-list">
          {files.map(file => (
            <div 
              key={file.path}
              className={`file-item ${selectedFile?.path === file.path ? 'selected' : ''}`}
              onClick={() => onFileSelect(file)}
            >
              <span>{file.name}</span>
              <span className="file-category">{file.category}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FileBrowser;
