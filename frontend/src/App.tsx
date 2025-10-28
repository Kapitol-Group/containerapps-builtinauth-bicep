import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { MsalProvider } from '@azure/msal-react';
import LandingPage from './pages/LandingPage';
import TenderManagementPage from './pages/TenderManagementPage';
import { msalInstance, initializeMsal, useLogin } from './authConfig';
import './App.css';

function App() {
  const [msalInitialized, setMsalInitialized] = useState(false);

  useEffect(() => {
    initializeMsal()
      .then(() => {
        setMsalInitialized(true);
        console.log('MSAL initialized, login configured:', useLogin);
      })
      .catch((error) => {
        console.error('Failed to initialize MSAL:', error);
        setMsalInitialized(true); // Continue anyway
      });
  }, []);

  if (!msalInitialized) {
    return <div>Loading authentication...</div>;
  }

  const appContent = (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/tender/:tenderId" element={<TenderManagementPage />} />
        </Routes>
      </div>
    </Router>
  );

  // Only wrap with MsalProvider if MSAL is configured
  return useLogin ? (
    <MsalProvider instance={msalInstance}>{appContent}</MsalProvider>
  ) : (
    appContent
  );
}

export default App;
