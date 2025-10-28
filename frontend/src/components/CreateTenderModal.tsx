import React, { useState, useEffect } from 'react';
import { tendersApi, configApi } from '../services/api';
import { Tender } from '../types';
import { SharePointFilePicker } from './SharePointFilePicker';
import './CreateTenderModal.css';

interface CreateTenderModalProps {
  onClose: () => void;
  onTenderCreated: (tender: Tender) => void;
}

const CreateTenderModal: React.FC<CreateTenderModalProps> = ({ onClose, onTenderCreated }) => {
  const [name, setName] = useState('');
  const [sharepointPath, setSharepointPath] = useState('');
  const [outputLocation, setOutputLocation] = useState('');
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

    try {
      setLoading(true);
      setError('');
      
      const tender = await tendersApi.create({
        name: name.trim(),
        sharepoint_path: sharepointPath.trim() || undefined,
        output_location: outputLocation.trim() || undefined,
      });
      
      onTenderCreated(tender);
    } catch (err: any) {
      setError(err.message || 'Failed to create tender');
    } finally {
      setLoading(false);
    }
  };

  const handleSharePointPathPicked = (data: any) => {
    console.log('SharePoint path picked:', data);
    
    // Extract the file/folder path from the picker result
    if (data.items && data.items.length > 0) {
      const item = data.items[0];
      // Build SharePoint URL from the picked item
      // Use webUrl if available, otherwise construct from endpoint and item details
      let path = '';
      
      if (item.webUrl) {
        path = item.webUrl;
      } else if (item['@sharePoint.endpoint'] && item.id) {
        // Construct path from endpoint and item ID
        const endpoint = item['@sharePoint.endpoint'];
        const baseUrl = endpoint.replace('/_api/v2.0', '');
        
        // If we have parentReference with driveId, we can construct a better path
        if (item.parentReference?.driveId) {
          path = `${baseUrl}/_layouts/15/DocLib.aspx?id=${item.id}`;
        } else {
          path = item['@sharePoint.embedUrl'] || `${baseUrl}/item/${item.id}`;
        }
      }
      
      console.log('Extracted SharePoint path:', path);
      setSharepointPath(path);
    }
  };

  const handleOutputLocationPicked = (data: any) => {
    console.log('Output location picked:', data);
    
    // Extract the folder path from the picker result
    if (data.items && data.items.length > 0) {
      const item = data.items[0];
      let path = '';
      
      if (item.webUrl) {
        path = item.webUrl;
      } else if (item['@sharePoint.endpoint'] && item.id) {
        const endpoint = item['@sharePoint.endpoint'];
        const baseUrl = endpoint.replace('/_api/v2.0', '');
        
        if (item.parentReference?.driveId) {
          path = `${baseUrl}/_layouts/15/DocLib.aspx?id=${item.id}`;
        } else {
          path = item['@sharePoint.embedUrl'] || `${baseUrl}/item/${item.id}`;
        }
      }
      
      console.log('Extracted output location:', path);
      setOutputLocation(path);
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

          <div className="form-group">
            <label htmlFor="sharepointPath">SharePoint Path</label>
            <div className="input-with-button">
              <input
                type="text"
                id="sharepointPath"
                value={sharepointPath}
                onChange={(e) => setSharepointPath(e.target.value)}
                placeholder="Select from SharePoint..."
                disabled={loading}
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
            <label htmlFor="outputLocation">Output Location</label>
            <div className="input-with-button">
              <input
                type="text"
                id="outputLocation"
                value={outputLocation}
                onChange={(e) => setOutputLocation(e.target.value)}
                placeholder="Select output location (optional)"
                disabled={loading}
              />
              <SharePointFilePicker
                baseUrl={sharePointBaseUrl}
                filters={['.folder']}
                onFilePicked={handleOutputLocationPicked}
                buttonText="Browse"
              />
            </div>
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
