import React from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Network from './pages/Network';
import MergeQueue from './pages/MergeQueue';
import GoldenHour from './pages/GoldenHour';
import Alerts from './pages/Alerts';
import AskCopilot from './pages/AskCopilot';
import Report from './pages/Report';
import Ledger from './pages/Ledger';
import Validation from './pages/Validation';
import Landing from './pages/Landing';
import Cases from './pages/Cases';
import CrossCase from './pages/CrossCase';

const ProtectedRoute = ({ children }) => {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/" replace />;
  }
  return children;
};

export const App = () => {
  return (
    <AuthProvider>
      <HashRouter>
        <Routes>
          {/* Public Landing Route */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Navigate to="/" replace />} />

          {/* Protected Workbench Routes */}
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/cases" element={<Cases />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/network" element={<Network />} />
            <Route path="/cross-case" element={<CrossCase />} />
            <Route path="/merge-queue" element={<MergeQueue />} />
            <Route path="/golden-hour" element={<GoldenHour />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/copilot" element={<AskCopilot />} />
            <Route path="/report" element={<Report />} />
            <Route path="/ledger" element={<Ledger />} />
            <Route path="/validation" element={<Validation />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </HashRouter>
    </AuthProvider>
  );
};

export default App;
