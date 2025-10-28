import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { tendersApi, filesApi, configApi } from '../services/api';
import { Tender, TenderFile } from '../types';
import FileUploadZone from '../components/FileUploadZone';
import SharePointFileBrowser from '../components/SharePointFileBrowser';
import FileBrowser from '../components/FileBrowser';
import FilePreview from '../components/FilePreview';
import ExtractionModal from '../components/ExtractionModal';
import Dialog from '../components/Dialog';
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
  const [config, setConfig] = useState<{ sharepointBaseUrl: string } | null>(null);
  const [alertDialog, setAlertDialog] = useState<{ show: boolean; message: string; title: string }>({ 
    show: false, 
    message: '', 
    title: '' 
  });

  useEffect(() => {
    loadConfig();
    if (tenderId) {
      loadTender();
      loadFiles();
    }
  }, [tenderId]);

  const loadConfig = async () => {
    try {
      const data = await configApi.get();
      setConfig({ sharepointBaseUrl: data.sharepointBaseUrl });
    } catch (error) {
      console.error('Failed to load config:', error);
    }
  };

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
      setAlertDialog({ 
        show: true, 
        title: 'No Files Selected', 
        message: 'Please select files for extraction' 
      });
    }
  };

  const handleFileDelete = async (file: TenderFile) => {
    if (!tenderId) return;
    
    try {
      await filesApi.delete(tenderId, file.path);
      
      // Remove from selected files if it was selected
      setSelectedFiles(prev => prev.filter(f => f.path !== file.path));
      
      // Clear preview if this was the previewed file
      if (selectedFile?.path === file.path) {
        setSelectedFile(null);
      }
      
      // Reload files list
      loadFiles();
    } catch (error) {
      console.error(`Failed to delete ${file.name}:`, error);
      setAlertDialog({ 
        show: true, 
        title: 'Delete Failed', 
        message: `Failed to delete file: ${error}` 
      });
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
        <div className="upload-section">
          <FileUploadZone onFilesDropped={handleFilesUploaded} />
          
          {config?.sharepointBaseUrl && (
            <SharePointFileBrowser
              tenderId={tenderId!}
              defaultSharePointPath={tender?.sharepoint_folder_path}
              sharepointBaseUrl={config.sharepointBaseUrl}
              onFilesImported={loadFiles}              
            />
          )}
        </div>
        
        <div className="file-workspace">
          <FileBrowser
            files={files}
            selectedFile={selectedFile}
            selectedFiles={selectedFiles}
            onFileSelect={handleFileSelect}
            onSelectionChange={setSelectedFiles}
            onFileDelete={handleFileDelete}
            loading={loading}
          />
          
          <FilePreview file={selectedFile} tenderId={tenderId} />
        </div>
      </div>

      {showExtractionModal && tenderId && (
        <ExtractionModal
          tenderId={tenderId}
          files={selectedFiles}
          onClose={() => setShowExtractionModal(false)}
          onSubmit={() => {
            setShowExtractionModal(false);
            setAlertDialog({ 
              show: true, 
              title: 'Success', 
              message: 'Extraction job queued successfully!' 
            });
          }}
        />
      )}

      <Dialog
        isOpen={alertDialog.show}
        title={alertDialog.title}
        message={alertDialog.message}
        type="alert"
        onConfirm={() => setAlertDialog({ show: false, message: '', title: '' })}
      />
    </div>
  );
};

export default TenderManagementPage;
