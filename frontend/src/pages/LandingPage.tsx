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
  const [deletingTenderId, setDeletingTenderId] = useState<string | null>(null);

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

  const handleDeleteClick = (e: React.MouseEvent, tenderId: string) => {
    e.stopPropagation(); // Prevent card click from triggering
    if (window.confirm('Are you sure you want to delete this tender? This will permanently delete all associated files.')) {
      deleteTender(tenderId);
    }
  };

  const deleteTender = async (tenderId: string) => {
    try {
      setDeletingTenderId(tenderId);
      await tendersApi.delete(tenderId);
      // Remove tender from state
      setTenders(tenders.filter(t => t.id !== tenderId));
    } catch (error) {
      console.error('Failed to delete tender:', error);
      alert('Failed to delete tender. Please try again.');
    } finally {
      setDeletingTenderId(null);
    }
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
                <div className="tender-card-header">
                  <h3>{tender.name}</h3>
                  <button
                    className="btn-delete"
                    onClick={(e) => handleDeleteClick(e, tender.id)}
                    disabled={deletingTenderId === tender.id}
                    aria-label="Delete tender"
                  >
                    {deletingTenderId === tender.id ? '...' : '×'}
                  </button>
                </div>
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
