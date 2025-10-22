import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { tendersApi, filesApi } from '../services/api';
import { Tender, TenderFile } from '../types';
import FileUploadZone from '../components/FileUploadZone';
import FileBrowser from '../components/FileBrowser';
import FilePreview from '../components/FilePreview';
import ExtractionModal from '../components/ExtractionModal';
import './TenderManagementPage.css';

const TenderManagementPage: React.FC = () => {
  const { tenderId } = useParams<{ tenderId: string }>();
  const navigate = useNavigate();
  
  const [tender, setTender] = useState<Tender | null>(null);
  const [files, setFiles] = useState<TenderFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<TenderFile | null>(null);
  const [showExtractionModal, setShowExtractionModal] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<TenderFile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (tenderId) {
      loadTender();
      loadFiles();
    }
  }, [tenderId]);

  const loadTender = async () => {
    if (!tenderId) return;
    try {
      const data = await tendersApi.get(tenderId);
      setTender(data);
    } catch (error) {
      console.error('Failed to load tender:', error);
    }
  };

  const loadFiles = async () => {
    if (!tenderId) return;
    try {
      setLoading(true);
      const data = await filesApi.list(tenderId);
      setFiles(data);
    } catch (error) {
      console.error('Failed to load files:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilesUploaded = async (uploadedFiles: File[]) => {
    if (!tenderId) return;
    
    for (const file of uploadedFiles) {
      try {
        await filesApi.upload(tenderId, file);
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error);
      }
    }
    
    loadFiles();
  };

  const handleFileSelect = (file: TenderFile) => {
    setSelectedFile(file);
  };

  const handleQueueExtraction = () => {
    if (selectedFiles.length > 0) {
      setShowExtractionModal(true);
    } else {
      alert('Please select files for extraction');
    }
  };

  return (
    <div className="tender-management-page">
      <header className="page-header">
        <button className="back-btn" onClick={() => navigate('/')}>
          ← Back
        </button>
        <h1>{tender?.name || 'Loading...'}</h1>
        <div className="header-actions">
          <button 
            className="btn-primary" 
            onClick={handleQueueExtraction}
            disabled={selectedFiles.length === 0}
          >
            Queue Extraction ({selectedFiles.length})
          </button>
        </div>
      </header>

      <div className="page-content">
        <FileUploadZone onFilesDropped={handleFilesUploaded} />
        
        <div className="file-workspace">
          <FileBrowser
            files={files}
            selectedFile={selectedFile}
            selectedFiles={selectedFiles}
            onFileSelect={handleFileSelect}
            onSelectionChange={setSelectedFiles}
            loading={loading}
          />
          
          <FilePreview file={selectedFile} />
        </div>
      </div>

      {showExtractionModal && tenderId && (
        <ExtractionModal
          tenderId={tenderId}
          files={selectedFiles}
          onClose={() => setShowExtractionModal(false)}
          onSubmit={() => {
            setShowExtractionModal(false);
            alert('Extraction job queued successfully!');
          }}
        />
      )}
    </div>
  );
};

export default TenderManagementPage;
