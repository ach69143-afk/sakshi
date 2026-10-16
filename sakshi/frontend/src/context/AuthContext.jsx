import React, { createContext, useContext, useState, useEffect } from 'react';
import { loginApi, demoLoginApi, authState } from '../api';

import QRCode from 'qrcode';

const AuthContext = createContext(null);

export const SEED_USERS = [
  { email: 'ig@demo.in', name: 'IG V. Sharma (IPS)', role: 'ig', label: 'Inspector General of Police (IG Range)' },
  { email: 'spdysp@demo.in', name: 'SP A. Kashyap (IPS)', role: 'sp_dysp', label: 'Superintendent of Police (Durg)' },
  { email: 'spraipur@demo.in', name: 'SP M. Sen (IPS)', role: 'sp_dysp_raipur', label: 'Superintendent of Police (Raipur)' },
  { email: 'cybercell@demo.in', name: 'Insp. P. Nayak (Cyber)', role: 'cyber_cell', label: 'Cyber Crime Cell Inspector' },
  { email: 'headconstable@demo.in', name: 'HC S. Deshmukh', role: 'head_constable', label: 'Head Constable (Investigator)' },
  { email: 'constable@demo.in', name: 'Constable R. Verma', role: 'constable', label: 'Field Constable' },
  { email: 'auditor@demo.in', name: 'Auditor M. Raman', role: 'auditor', label: 'Judicial / Forensic Auditor' },
];

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => authState.getUser());
  const [token, setToken] = useState(() => authState.getToken());
  const [debugMode, setDebugMode] = useState(false);

  const demoLogin = async (name, email, role, website = '') => {
    const res = await demoLoginApi(name, email, role, website);
    setToken(res.token);
    setUser(res.user);
    authState.setAuth(res.token, res.user);
    return res;
  };

  const login = async (email, password, totp_code = null) => {
    try {
      const res = await loginApi(email, password, totp_code);
      if (res && res.mfa_required) {
        return res;
      }
      setToken(res.token);
      setUser(res.user);
      authState.setAuth(res.token, res.user);
      return res.user;
    } catch (err) {
      // Fallback for static GitHub Pages / demo mode
      const seedMatch = SEED_USERS.find(u => u.email === email);
      if (seedMatch && password === 'demo123') {
        if (!totp_code) {
          const step = Math.floor(Date.now() / 30000);
          const fallbackCode = String((step * 48271) % 900000 + 100000);
          const qrDataUri = await QRCode.toDataURL(fallbackCode, { margin: 1, width: 256 });
          const qrAuthUri = await QRCode.toDataURL(`otpauth://totp/SAKSHI:${encodeURIComponent(seedMatch.email)}?secret=JBSWY3DPEHPK3PXP&issuer=SAKSHI`, { margin: 1, width: 256 });
          return {
            mfa_required: true,
            email: seedMatch.email,
            name: seedMatch.name,
            role: seedMatch.role,
            enrolled: true,
            secret: 'JBSWY3DPEHPK3PXP',
            current_code: fallbackCode,
            qr_code: qrDataUri,
            qr_code_auth: qrAuthUri,
            expires_in: 30 - (Math.floor(Date.now() / 1000) % 30),
            detail: `Scan the QR code with your phone camera to display your 6-digit code: ${fallbackCode}`
          };
        }
        const fallbackUser = { email: seedMatch.email, name: seedMatch.name, role: seedMatch.role };
        const fallbackToken = `token_${seedMatch.role}_offline`;
        setToken(fallbackToken);
        setUser(fallbackUser);
        authState.setAuth(fallbackToken, fallbackUser);
        return fallbackUser;
      }
      throw err;
    }
  };

  const switchRoleDirectly = async (targetEmail) => {
    const target = SEED_USERS.find(u => u.email === targetEmail) || SEED_USERS[0];
    try {
      const res = await loginApi(target.email, 'demo123');
      setToken(res.token);
      setUser(res.user);
      authState.setAuth(res.token, res.user);
      return res.user;
    } catch {
      const newToken = `token_${target.role}_${Date.now()}`;
      const newUser = { email: target.email, name: target.name, role: target.role };
      setToken(newToken);
      setUser(newUser);
      authState.setAuth(newToken, newUser);
      return newUser;
    }
  };

  const logout = () => {
    authState.clearAuth();
    setUser(null);
    setToken(null);
  };

  const hasRole = (allowedRoles) => {
    if (!user) return false;
    return allowedRoles.includes(user.role);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, demoLogin, logout, switchRoleDirectly, hasRole, debugMode, setDebugMode }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
