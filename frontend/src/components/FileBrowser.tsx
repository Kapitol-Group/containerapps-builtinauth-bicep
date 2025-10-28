import React from 'react';
import { TenderFile } from '../types';

interface FileBrowserProps {
  files: TenderFile[];
  selectedFile: TenderFile | null;
  selectedFiles: TenderFile[];
  onFileSelect: (file: TenderFile) => void;
  onSelectionChange: (files: TenderFile[]) => void;
  onFileDelete?: (file: TenderFile) => void;
  loading: boolean;
}

const FileBrowser: React.FC<FileBrowserProps> = ({ 
  files, 
  selectedFile, 
  selectedFiles, 
  onFileSelect, 
  onSelectionChange, 
  onFileDelete,
  loading 
}) => {
  const handleFileClick = (file: TenderFile, event: React.MouseEvent) => {
    // Set as preview file
    onFileSelect(file);
    
    // Handle multi-selection
    if (event.ctrlKey || event.metaKey) {
      // Ctrl/Cmd+click: toggle selection
      const isSelected = selectedFiles.some(f => f.path === file.path);
      if (isSelected) {
        onSelectionChange(selectedFiles.filter(f => f.path !== file.path));
      } else {
        onSelectionChange([...selectedFiles, file]);
      }
    } else if (event.shiftKey && selectedFiles.length > 0) {
      // Shift+click: select range
      const lastSelectedIndex = files.findIndex(f => f.path === selectedFiles[selectedFiles.length - 1].path);
      const currentIndex = files.findIndex(f => f.path === file.path);
      const start = Math.min(lastSelectedIndex, currentIndex);
      const end = Math.max(lastSelectedIndex, currentIndex);
      onSelectionChange(files.slice(start, end + 1));
    } else {
      // Regular click: select single file
      onSelectionChange([file]);
    }
  };

  const handleCheckboxChange = (file: TenderFile, checked: boolean) => {
    if (checked) {
      onSelectionChange([...selectedFiles, file]);
    } else {
      onSelectionChange(selectedFiles.filter(f => f.path !== file.path));
    }
  };

  const isFileSelected = (file: TenderFile) => {
    return selectedFiles.some(f => f.path === file.path);
  };

  const handleSelectAll = () => {
    if (selectedFiles.length === files.length) {
      // Deselect all
      onSelectionChange([]);
    } else {
      // Select all
      onSelectionChange([...files]);
    }
  };

  const allSelected = files.length > 0 && selectedFiles.length === files.length;

  const handleDeleteClick = (file: TenderFile, event: React.MouseEvent) => {
    event.stopPropagation();
    if (onFileDelete && window.confirm(`Are you sure you want to delete "${file.name}"?`)) {
      onFileDelete(file);
    }
  };

  return (
    <div className="file-browser">
      <div className="file-browser-header">
        <h3>Files ({files.length})</h3>
        {files.length > 0 && (
          <button 
            className="select-all-btn"
            onClick={handleSelectAll}
            title={allSelected ? "Deselect all" : "Select all"}
          >
            {allSelected ? '☑ Deselect All' : '☐ Select All'}
          </button>
        )}
      </div>
      {loading ? <p>Loading...</p> : (
        <div className="file-list">
          {files.map(file => (
            <div 
              key={file.path}
              className={`file-item ${selectedFile?.path === file.path ? 'active' : ''} ${isFileSelected(file) ? 'selected' : ''}`}
              onClick={(e) => handleFileClick(file, e)}
            >
              <input
                type="checkbox"
                checked={isFileSelected(file)}
                onChange={(e) => {
                  e.stopPropagation();
                  handleCheckboxChange(file, e.target.checked);
                }}
                onClick={(e) => e.stopPropagation()}
              />
              <span className="file-name">{file.name}</span>
              <span className="file-category">{file.category}</span>
              {onFileDelete && (
                <button
                  className="delete-file-btn"
                  onClick={(e) => handleDeleteClick(file, e)}
                  title="Delete file"
                  aria-label="Delete file"
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FileBrowser;
