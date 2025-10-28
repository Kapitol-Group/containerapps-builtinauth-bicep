import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { tendersApi } from '../services/api';
import { Tender } from '../types';
import CreateTenderModal from '../components/CreateTenderModal';
import './LandingPage.css';

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [filteredTenders, setFilteredTenders] = useState<Tender[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    loadTenders();
  }, []);

  useEffect(() => {
    if (searchTerm) {
      setFilteredTenders(
        tenders.filter((tender) =>
          tender.name.toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    } else {
      setFilteredTenders(tenders);
    }
  }, [searchTerm, tenders]);

  const loadTenders = async () => {
    try {
      setLoading(true);
      const data = await tendersApi.list();
      setTenders(data);
      setFilteredTenders(data);
    } catch (error) {
      console.error('Failed to load tenders:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTenderClick = (tenderId: string) => {
    navigate(`/tender/${tenderId}`);
  };

  const handleTenderCreated = (tender: Tender) => {
    setTenders([tender, ...tenders]);
    setShowCreateModal(false);
    navigate(`/tender/${tender.id}`);
  };

  return (
    <div className="landing-page">
      <header className="header">
        <h1>Construction Tender Document Automation</h1>
        <div className="header-actions">
          <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
            + Create New Tender
          </button>
        </div>
      </header>

      <div className="content">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search tenders..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        {loading ? (
          <div className="loading">Loading tenders...</div>
        ) : filteredTenders.length === 0 ? (
          <div className="empty-state">
            <p>No tenders found.</p>
            <button className="btn-secondary" onClick={() => setShowCreateModal(true)}>
              Create your first tender
            </button>
          </div>
        ) : (
          <div className="tenders-grid">
            {filteredTenders.map((tender) => (
              <div
                key={tender.id}
                className="tender-card"
                onClick={() => handleTenderClick(tender.id)}
              >
                <h3>{tender.name}</h3>
                <div className="tender-meta">
                  <span>Files: {tender.file_count}</span>
                  <span>Created: {tender.created_at ? new Date(tender.created_at).toLocaleDateString() : 'Unknown'}</span>
                </div>
                <div className="tender-footer">
                  <span className="created-by">By {tender.created_by || 'Unknown'}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showCreateModal && (
        <CreateTenderModal
          onClose={() => setShowCreateModal(false)}
          onTenderCreated={handleTenderCreated}
        />
      )}
    </div>
  );
};

export default LandingPage;
