import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { tendersApi, filesApi, configApi, batchesApi } from '../services/api';
import { Tender, TenderFile } from '../types';
import FileUploadZone from '../components/FileUploadZone';
import SharePointFileBrowser from '../components/SharePointFileBrowser';
import FileBrowser from '../components/FileBrowser';
import FilePreview from '../components/FilePreview';
import ExtractionModal from '../components/ExtractionModal';
import BatchesTab from '../components/BatchesTab';
import Dialog from '../components/Dialog';
import './TenderManagementPage.css';

type MainTab = 'files' | 'batches';

const TenderManagementPage: React.FC = () => {
  const { tenderId } = useParams<{ tenderId: string }>();
  const navigate = useNavigate();
  
  const [tender, setTender] = useState<Tender | null>(null);
  const [files, setFiles] = useState<TenderFile[]>([]);
  const [activeFiles, setActiveFiles] = useState<TenderFile[]>([]);
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

  // Main tab navigation
  const [activeTab, setActiveTab] = useState<MainTab>('files');

  // Reload files when tab changes to ensure correct filtering
  useEffect(() => {
    if (tenderId && activeTab === 'files') {
      loadFiles();
    }
  }, [activeTab]);

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
      // When on "files" tab, exclude batched files
      const excludeBatched = activeTab === 'files';
      const data = await filesApi.list(tenderId, excludeBatched);
      setFiles(data);
      
      // Update activeFiles when in files tab
      if (activeTab === 'files') {
        setActiveFiles(data);
      }
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
        {/* Top-level tab navigation */}
        <div className="main-tabs">
          <button
            className={`tab-button ${activeTab === 'files' ? 'active' : ''}`}
            onClick={() => setActiveTab('files')}
          >
            Files
            {activeFiles.length > 0 && <span className="tab-badge">{activeFiles.length}</span>}
          </button>
          <button
            className={`tab-button ${activeTab === 'batches' ? 'active' : ''}`}
            onClick={() => setActiveTab('batches')}
          >
            Batches
          </button>
        </div>

        {/* Tab content */}
        {activeTab === 'files' && (
          <>
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
                files={activeFiles}
                selectedFile={selectedFile}
                selectedFiles={selectedFiles}
                onFileSelect={handleFileSelect}
                onSelectionChange={setSelectedFiles}
                onFileDelete={handleFileDelete}
                loading={loading}
              />
              
              <FilePreview file={selectedFile} tenderId={tenderId} />
            </div>
          </>
        )}

        {activeTab === 'batches' && tenderId && (
          <BatchesTab
            tenderId={tenderId}
            onError={(message) => setAlertDialog({ show: true, title: 'Error', message })}
            onReloadFiles={loadFiles}
          />
        )}
      </div>

      {showExtractionModal && tenderId && (
        <ExtractionModal
          tenderId={tenderId}
          tenderName={tender?.name}
          files={selectedFiles}
          onClose={() => setShowExtractionModal(false)}
          onSubmit={() => {
            setShowExtractionModal(false);
            
            // Reload files
            loadFiles();
            
            // Clear selection
            setSelectedFiles([]);
            
            // Switch to batches tab
            setActiveTab('batches');

            // Clear pdf preview
            setSelectedFile(null);
            
            setAlertDialog({ 
              show: true, 
              title: 'Batch Queued Successfully', 
              message: 'Your extraction batch has been queued and is processing in the background. Check the Batches tab for status updates.' 
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
