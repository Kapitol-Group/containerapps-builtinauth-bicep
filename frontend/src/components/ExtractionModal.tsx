import React, { useState } from 'react';
import { TenderFile, TitleBlockCoords } from '../types';
import { uipathApi } from '../services/api';

interface ExtractionModalProps {
  tenderId: string;
  files: TenderFile[];
  onClose: () => void;
  onSubmit: () => void;
}

const ExtractionModal: React.FC<ExtractionModalProps> = ({ tenderId, files, onClose, onSubmit }) => {
  const [discipline, setDiscipline] = useState('Architectural');
  const [coords, setCoords] = useState<TitleBlockCoords>({ x: 0, y: 0, width: 100, height: 50 });

  const handleSubmit = async () => {
    try {
      await uipathApi.queueExtraction(
        tenderId,
        files.map(f => f.path),
        discipline,
        coords
      );
      onSubmit();
    } catch (error) {
      console.error('Failed to queue extraction:', error);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Queue Extraction</h2>
        <div className="form-group">
          <label>Discipline</label>
          <select value={discipline} onChange={(e) => setDiscipline(e.target.value)}>
            <option>Architectural</option>
            <option>Structural</option>
            <option>Mechanical</option>
            <option>Electrical</option>
          </select>
        </div>
        <p>Title block region selection tool coming soon</p>
        <div className="modal-footer">
          <button onClick={onClose}>Cancel</button>
          <button onClick={handleSubmit}>Submit</button>
        </div>
      </div>
    </div>
  );
};

export default ExtractionModal;
