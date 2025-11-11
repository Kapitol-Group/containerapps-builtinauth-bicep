import React, { useState, useEffect } from 'react';
import { tendersApi, configApi } from '../services/api';
import { Tender } from '../types';
import { SharePointFilePicker } from './SharePointFilePicker';
import { extractSharePointIdentifiersWithPath } from '../utils/sharepoint';
import { getGraphApiToken } from '../authConfig';
import './CreateTenderModal.css';

interface CreateTenderModalProps {
  onClose: () => void;
  onTenderCreated: (tender: Tender) => void;
}

const CreateTenderModal: React.FC<CreateTenderModalProps> = ({ onClose, onTenderCreated }) => {
  const [name, setName] = useState('');
  const [sharepointPath, setSharepointPath] = useState('');
  
  // SharePoint identifiers for the tender location
  const [sharepointsiteid, setSharepointsiteid] = useState('');
  const [sharepointlibraryid, setSharepointlibraryid] = useState('');
  const [sharepointfolderpath, setSharepointfolderpath] = useState('');
  
  // Output location identifiers
  const [outputLocation, setOutputLocation] = useState('');
  const [outputSiteId, setOutputSiteId] = useState('');
  const [outputLibraryId, setOutputLibraryId] = useState('');
  const [outputFolderPath, setOutputFolderPath] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sharePointBaseUrl, setSharePointBaseUrl] = useState<string>('');
  const [configLoading, setConfigLoading] = useState(true);

  // Fetch configuration from backend on mount
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const config = await configApi.get();
        if (!config.sharepointBaseUrl) {
          setError('SharePoint URL is not configured on the server. Please contact administrator.');
        } else {
          setSharePointBaseUrl(config.sharepointBaseUrl);
        }
      } catch (err: any) {
        setError('Failed to load configuration: ' + (err.message || 'Unknown error'));
      } finally {
        setConfigLoading(false);
      }
    };
    
    fetchConfig();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!name.trim()) {
      setError('Tender name is required');
      return;
    }

    if (!sharepointsiteid || !sharepointlibraryid || !sharepointfolderpath) {
      setError('SharePoint Path is required');
      return;
    }

    if (!outputSiteId || !outputLibraryId || !outputFolderPath) {
      setError('Output Location is required');
      return;
    }

    try {
      setLoading(true);
      setError('');
      
      const tender = await tendersApi.create({
        name: name.trim(),
        // Send the three SharePoint identifiers
        sharepoint_site_id: sharepointsiteid || undefined,
        sharepoint_library_id: sharepointlibraryid || undefined,
        sharepoint_folder_path: sharepointfolderpath || undefined,
        // Output location identifiers
        output_site_id: outputSiteId || undefined,
        output_library_id: outputLibraryId || undefined,
        output_folder_path: outputFolderPath || undefined,
      });
      
      onTenderCreated(tender);
    } catch (err: any) {
      setError(err.message || 'Failed to create tender');
    } finally {
      setLoading(false);
    }
  };

  const handleSharePointPathPicked = async (data: any) => {
    console.log('SharePoint path picked - FULL DATA:', JSON.stringify(data, null, 2));
    
    try {
      // Get access token for Graph API using runtime backend config
      let accessToken: string | undefined;
      try {
        accessToken = await getGraphApiToken('https://graph.microsoft.com');
        console.log('Got Graph API token for path lookup');
      } catch (tokenError) {
        console.warn('Could not get Graph API token, will try without it:', tokenError);
      }

      // Extract SharePoint identifiers from the picker result (with optional Graph API lookup)
      const identifiers = await extractSharePointIdentifiersWithPath(data, accessToken);
      
      if (identifiers) {
        console.log('Extracted SharePoint identifiers:', identifiers);
        console.log('Path source:', identifiers.pathSource);
        
        // Set the three identifiers
        setSharepointsiteid(identifiers.sharepointsiteid);
        setSharepointlibraryid(identifiers.sharepointlibraryid);
        setSharepointfolderpath(identifiers.sharepointfolderpath);
        
        // Set a display-friendly path for the UI
        if (identifiers.sharepointfolderpath) {
          const sourceLabel = identifiers.pathSource === 'graphApi' ? ' (via Graph API)' : '';
          setSharepointPath(identifiers.sharepointfolderpath + sourceLabel);
          
          // Auto-populate Tender Name with the folder name
          const folderName = identifiers.sharepointfolderpath.split('/').filter(Boolean).pop() || '';
          if (folderName && !name) {
            setName(folderName);
          }
        } else {
          setSharepointPath('Selected (path unavailable - check console)');
          console.warn('Folder path is unavailable despite Graph API attempt');
        }
      } else {
        console.error('Failed to extract SharePoint identifiers');
        setError('Failed to extract SharePoint information. Please try again.');
      }
    } catch (err) {
      console.error('Error in handleSharePointPathPicked:', err);
      setError('An error occurred while processing the SharePoint selection.');
    }
  };

  const handleOutputLocationPicked = async (data: any) => {
    console.log('Output location picked:', data);
    
    try {
      // Get access token for Graph API using runtime backend config
      let accessToken: string | undefined;
      try {
        accessToken = await getGraphApiToken('https://graph.microsoft.com');
      } catch (tokenError) {
        console.warn('Could not get Graph API token:', tokenError);
      }

      // Extract SharePoint identifiers for output location
      const identifiers = await extractSharePointIdentifiersWithPath(data, accessToken);
      
      if (identifiers) {
        console.log('Extracted output location identifiers:', identifiers);
        console.log('Path source:', identifiers.pathSource);
        
        // Set the output location identifiers
        setOutputSiteId(identifiers.sharepointsiteid);
        setOutputLibraryId(identifiers.sharepointlibraryid);
        setOutputFolderPath(identifiers.sharepointfolderpath);
        
        // Set a display-friendly path for the UI
        if (identifiers.sharepointfolderpath) {
          const sourceLabel = identifiers.pathSource === 'graphApi' ? ' (via Graph API)' : '';
          setOutputLocation(identifiers.sharepointfolderpath + sourceLabel);
        } else {
          setOutputLocation('Selected (path unavailable)');
        }
      } else {
        console.error('Failed to extract output location identifiers');
        setError('Failed to extract output location information. Please try again.');
      }
    } catch (err) {
      console.error('Error in handleOutputLocationPicked:', err);
      setError('An error occurred while processing the output location selection.');
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create New Tender</h2>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        {configLoading ? (
          <div style={{ padding: '2rem', textAlign: 'center' }}>
            Loading configuration...
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="sharepointPath">SharePoint Path *</label>
            <div className="input-with-button">
              <input
                type="text"
                id="sharepointPath"
                value={sharepointPath}
                placeholder="Select from SharePoint..."
                disabled={loading}
                readOnly
                required
              />
              <SharePointFilePicker
                baseUrl={sharePointBaseUrl}
                filters={['.folder']}
                onFilePicked={handleSharePointPathPicked}
                buttonText="Browse"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="outputLocation">Output Location *</label>
            <div className="input-with-button">
              <input
                type="text"
                id="outputLocation"
                value={outputLocation}
                placeholder="Select output location..."
                disabled={loading}
                readOnly
                required
              />
              <SharePointFilePicker
                baseUrl={sharePointBaseUrl}
                filters={['.folder']}
                onFilePicked={handleOutputLocationPicked}
                buttonText="Browse"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="name">Tender Name *</label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter tender name"
              disabled={loading}
              required
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create Tender'}
            </button>
          </div>
        </form>
        )}
      </div>
    </div>
  );
};

export default CreateTenderModal;
