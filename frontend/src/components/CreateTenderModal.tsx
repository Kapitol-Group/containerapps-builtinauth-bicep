import React, { useState, useEffect } from 'react';
import { tendersApi, configApi, mfilesApi } from '../services/api';
import { Tender } from '../types';
import { SharePointFilePicker } from './SharePointFilePicker';
import { extractSharePointIdentifiersWithPath } from '../utils/sharepoint';
import { getGraphApiToken } from '../authConfig';
import './CreateTenderModal.css';

interface CreateTenderModalProps {
  onClose: () => void;
  onTenderCreated: (tender: Tender) => void;
}

type TenderType = 'sharepoint' | 'mfiles';

interface MFilesProject {
  id: string;
  name: string;
}

const CreateTenderModal: React.FC<CreateTenderModalProps> = ({ onClose, onTenderCreated }) => {
  const [name, setName] = useState('');
  const [tenderType, setTenderType] = useState<TenderType>('sharepoint');
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

  // M-Files project selection
  const [mfilesProjects, setMfilesProjects] = useState<MFilesProject[]>([]);
  const [mfilesProjectId, setMfilesProjectId] = useState('');
  const [mfilesProjectName, setMfilesProjectName] = useState('');
  const [mfilesLoading, setMfilesLoading] = useState(false);
  const [mfilesLoaded, setMfilesLoaded] = useState(false);
  const [mfilesError, setMfilesError] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sharePointBaseUrl, setSharePointBaseUrl] = useState<string>('');
  const [configLoading, setConfigLoading] = useState(true);
  const [configError, setConfigError] = useState('');

  // Fetch configuration from backend on mount.
  // This is required only for SharePoint tender type.
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const config = await configApi.get();
        setSharePointBaseUrl(config.sharepointBaseUrl || '');
      } catch (err: any) {
        setConfigError('Failed to load configuration: ' + (err.message || 'Unknown error'));
      } finally {
        setConfigLoading(false);
      }
    };

    fetchConfig();
  }, []);

  const loadMFilesProjects = async () => {
    setMfilesLoading(true);
    setMfilesError('');

    try {
      const projects = await mfilesApi.listProjects();
      setMfilesProjects(projects);
      setMfilesLoaded(true);

      if (projects.length === 0) {
        setMfilesError('No projects were returned from M-Files.');
      }
    } catch (err: any) {
      setMfilesError(err.message || 'Failed to load M-Files projects');
    } finally {
      setMfilesLoading(false);
    }
  };

  useEffect(() => {
    if (tenderType === 'mfiles' && !mfilesLoaded && !mfilesLoading && !mfilesError) {
      loadMFilesProjects();
    }
  }, [tenderType, mfilesLoaded, mfilesLoading, mfilesError]);

  const handleTenderTypeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const nextType = event.target.value as TenderType;
    setTenderType(nextType);
    setError('');
  };

  const handleMFilesProjectChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const projectId = event.target.value;
    setMfilesProjectId(projectId);

    const project = mfilesProjects.find((p) => p.id === projectId);
    const projectName = project?.name || '';
    setMfilesProjectName(projectName);

    if (projectName && !name) {
      setName(projectName);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      setError('Tender name is required');
      return;
    }

    if (tenderType === 'sharepoint') {
      if (configLoading) {
        setError('SharePoint configuration is still loading. Please try again.');
        return;
      }

      if (configError || !sharePointBaseUrl) {
        setError('SharePoint URL is not configured on the server. Please contact administrator.');
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
    }

    if (tenderType === 'mfiles' && (!mfilesProjectId || !mfilesProjectName)) {
      setError('M-Files Project is required');
      return;
    }

    try {
      setLoading(true);
      setError('');

      const payload: Parameters<typeof tendersApi.create>[0] = {
        name: name.trim(),
        tender_type: tenderType,
      };

      if (tenderType === 'sharepoint') {
        // Send the three SharePoint identifiers
        payload.sharepoint_site_id = sharepointsiteid || undefined;
        payload.sharepoint_library_id = sharepointlibraryid || undefined;
        payload.sharepoint_folder_path = sharepointfolderpath || undefined;
        // Output location identifiers
        payload.output_site_id = outputSiteId || undefined;
        payload.output_library_id = outputLibraryId || undefined;
        payload.output_folder_path = outputFolderPath || undefined;
      } else {
        payload.mfiles_project_id = mfilesProjectId;
        payload.mfiles_project_name = mfilesProjectName;
      }

      const tender = await tendersApi.create(payload);
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

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="tenderType">Tender Type *</label>
            <select
              id="tenderType"
              value={tenderType}
              onChange={handleTenderTypeChange}
              disabled={loading}
              required
            >
              <option value="sharepoint">SharePoint</option>
              <option value="mfiles">M-Files</option>
            </select>
          </div>

          {tenderType === 'sharepoint' && (
            <>
              {configLoading ? (
                <div style={{ padding: '0.75rem 0', color: 'var(--text-secondary)' }}>
                  Loading SharePoint configuration...
                </div>
              ) : (
                <>
                  {!sharePointBaseUrl && (
                    <div className="error-message">
                      SharePoint URL is not configured on the server. Please contact administrator.
                    </div>
                  )}

                  {configError && (
                    <div className="error-message">
                      {configError}
                    </div>
                  )}

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
                      {sharePointBaseUrl && (
                        <SharePointFilePicker
                          baseUrl={sharePointBaseUrl}
                          filters={['.folder']}
                          onFilePicked={handleSharePointPathPicked}
                          buttonText="Browse"
                        />
                      )}
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
                      {sharePointBaseUrl && (
                        <SharePointFilePicker
                          baseUrl={sharePointBaseUrl}
                          filters={['.folder']}
                          onFilePicked={handleOutputLocationPicked}
                          buttonText="Browse"
                        />
                      )}
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          {tenderType === 'mfiles' && (
            <div className="form-group">
              <label htmlFor="mfilesProject">Project *</label>
              <select
                id="mfilesProject"
                value={mfilesProjectId}
                onChange={handleMFilesProjectChange}
                disabled={loading || mfilesLoading}
                required
              >
                <option value="">
                  {mfilesLoading
                    ? 'Loading projects...'
                    : mfilesProjects.length > 0
                      ? 'Select a project'
                      : 'No projects available'}
                </option>
                {mfilesProjects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>

              <div style={{ marginTop: '0.5rem' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={loadMFilesProjects}
                  disabled={loading || mfilesLoading}
                >
                  {mfilesLoading ? 'Loading...' : 'Reload Projects'}
                </button>
              </div>

              {mfilesError && <div className="error-message" style={{ marginTop: '0.75rem' }}>{mfilesError}</div>}
            </div>
          )}

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
      </div>
    </div>
  );
};

export default CreateTenderModal;
