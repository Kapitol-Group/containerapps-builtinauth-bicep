import React, { useState } from 'react';
import { tendersApi } from '../services/api';
import { Tender } from '../types';
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

  const handleSharePointPicker = () => {
    // TODO: Integrate SharePoint FilePicker
    alert('SharePoint FilePicker integration coming soon');
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
              <button
                type="button"
                className="btn-secondary"
                onClick={handleSharePointPicker}
                disabled={loading}
              >
                Browse
              </button>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="outputLocation">Output Location</label>
            <input
              type="text"
              id="outputLocation"
              value={outputLocation}
              onChange={(e) => setOutputLocation(e.target.value)}
              placeholder="Enter output location (optional)"
              disabled={loading}
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
      </div>
    </div>
  );
};

export default CreateTenderModal;
