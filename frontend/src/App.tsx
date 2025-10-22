import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import TenderManagementPage from './pages/TenderManagementPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/tender/:tenderId" element={<TenderManagementPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
