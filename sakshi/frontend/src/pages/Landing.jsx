import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Shield, 
  Lock, 
  Mail, 
  ArrowRight, 
  UserCheck, 
  AlertCircle, 
  Database, 
  GitMerge, 
  AlertTriangle, 
  FileCheck2, 
  Activity, 
  Clock, 
  Cpu, 
  Search, 
  Network, 
  Layers, 
  Fingerprint,
  Info,
  CheckCircle2,
  QrCode,
  Smartphone,
  RefreshCw,
  Copy,
  Check
} from 'lucide-react';
import QRCode from 'qrcode';
import { useAuth, SEED_USERS } from '../context/AuthContext';
import { getPublicSummaryApi, refreshMfaApi } from '../api';
import MapBackdrop from '../components/MapBackdrop';

export const Landing = () => {
  const { user, login, demoLogin } = useAuth();
  const navigate = useNavigate();
  const authSectionRef = useRef(null);

  // Sign-in tabs: 'demo' | 'official'
  const [activeTab, setActiveTab] = useState('demo');

  // Demo Login form state
  const [demoName, setDemoName] = useState('');
  const [demoEmail, setDemoEmail] = useState('');
  const [demoRole, setDemoRole] = useState('SP / DySP');
  const [honeypot, setHoneypot] = useState('');
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState('');
  const [demoNoticeStatus, setDemoNoticeStatus] = useState(null);

  // Official Sign-in form state
  const [officialEmail, setOfficialEmail] = useState('spdysp@demo.in');
  const [officialPassword, setOfficialPassword] = useState('demo123');
  const [officialLoading, setOfficialLoading] = useState(false);
  const [officialError, setOfficialError] = useState('');
  const [mfaChallenge, setMfaChallenge] = useState(null);
  const [totpCode, setTotpCode] = useState('');
  const [qrMode, setQrMode] = useState('camera'); // 'camera' | 'authenticator'
  const [timeLeft, setTimeLeft] = useState(30);
  const [codeCopied, setCodeCopied] = useState(false);
  const [refreshingMfa, setRefreshingMfa] = useState(false);

  // Live counters from public summary
  const [summary, setSummary] = useState({
    entities: '--',
    calls: '--',
    transactions: '--',
    alerts: '--',
    loading: true
  });

  useEffect(() => {
    let isMounted = true;
    getPublicSummaryApi()
      .then((data) => {
        if (isMounted) {
          setSummary({
            entities: data.entities ?? 0,
            calls: data.calls ?? 0,
            transactions: data.transactions ?? 0,
            alerts: data.alerts ?? 0,
            loading: false
          });
        }
      })
      .catch(() => {
        if (isMounted) {
          // Fallback static counts if backend offline
          setSummary({
            entities: 63,
            calls: 400,
            transactions: 150,
            alerts: 8,
            loading: false
          });
        }
      });
    return () => { isMounted = false; };
  }, []);

  const scrollToAuth = (tab) => {
    setActiveTab(tab);
    if (authSectionRef.current) {
      authSectionRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleDemoSubmit = async (e) => {
    e.preventDefault();
    setDemoError('');
    setDemoNoticeStatus(null);

    if (!demoName.trim()) {
      setDemoError('Please enter your name.');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!demoEmail.trim() || !emailRegex.test(demoEmail.trim())) {
      setDemoError('Please enter a valid email address.');
      return;
    }

    setDemoLoading(true);
    try {
      const res = await demoLogin(demoName.trim(), demoEmail.trim(), demoRole, honeypot);
      if (res.notice_status === 'Login notice skipped (limit)') {
        setDemoNoticeStatus('Login notice skipped (limit)');
      }
      setTimeout(() => {
        navigate('/dashboard');
      }, 350);
    } catch (err) {
      setDemoError(err.response?.data?.detail || 'Demo login failed. Please try again.');
    } finally {
      setDemoLoading(false);
    }
  };

  // Live TOTP countdown and auto-refresh when MFA challenge is active
  useEffect(() => {
    if (!mfaChallenge) return;
    if (mfaChallenge.expires_in) {
      setTimeLeft(mfaChallenge.expires_in);
    }
    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          handleRefreshCode();
          return 30;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [mfaChallenge?.secret, mfaChallenge?.current_code]);

  const handleRefreshCode = async () => {
    if (!mfaChallenge) return;
    setRefreshingMfa(true);
    try {
      const res = await refreshMfaApi(mfaChallenge.email || officialEmail);
      if (res && res.current_code) {
        setMfaChallenge((prev) => ({ ...prev, ...res }));
        setTimeLeft(res.expires_in || 30);
      }
    } catch {
      // Fallback offline generation
      const step = Math.floor(Date.now() / 30000);
      const fallbackCode = String((step * 48271) % 900000 + 100000);
      try {
        const qrUri = await QRCode.toDataURL(fallbackCode, { margin: 1, width: 256 });
        const qrAuthUri = await QRCode.toDataURL(
          `otpauth://totp/SAKSHI:${encodeURIComponent(officialEmail)}?secret=${mfaChallenge.secret || 'JBSWY3DPEHPK3PXP'}&issuer=SAKSHI`,
          { margin: 1, width: 256 }
        );
        setMfaChallenge((prev) => ({
          ...prev,
          current_code: fallbackCode,
          qr_code: qrUri,
          qr_code_auth: qrAuthUri,
          expires_in: 30 - (Math.floor(Date.now() / 1000) % 30)
        }));
        setTimeLeft(30 - (Math.floor(Date.now() / 1000) % 30));
      } catch (err) {
        console.error('QR code generation error:', err);
      }
    } finally {
      setRefreshingMfa(false);
    }
  };

  const handleOfficialSubmit = async (e) => {
    e.preventDefault();
    setOfficialError('');
    setOfficialLoading(true);
    try {
      const res = await login(officialEmail, officialPassword, totpCode || null);
      if (res && res.mfa_required) {
        setMfaChallenge(res);
        if (res.expires_in) setTimeLeft(res.expires_in);
        setOfficialLoading(false);
        return;
      }
      navigate('/dashboard');
    } catch (err) {
      setOfficialError(err.response?.data?.detail || 'Invalid official credentials.');
    } finally {
      setOfficialLoading(false);
    }
  };

  const autofillOfficial = (seed) => {
    setOfficialEmail(seed.email);
    setOfficialPassword('demo123');
    setMfaChallenge(null);
    setTotpCode('');
    setTimeLeft(30);
  };

  return (
    <div className="min-h-screen bg-[#07080a] text-slate-100 flex flex-col font-sans selection:bg-red-950 selection:text-red-200">
      {/* Top Header / Navigation */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-red-600 to-red-900 flex items-center justify-center font-bold text-white text-base shadow-lg shadow-red-950/60 border border-red-500/40">
              सा
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold tracking-wider text-base text-slate-100">SAKSHI</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-red-950/80 text-red-300 border border-red-800/60">
                  DEFENSIBLE AI
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono tracking-tight hidden sm:block">
                STATE POLICE CYBER CELL • EVIDENTIARY ANALYSIS SUITE
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {user ? (
              <button
                onClick={() => navigate('/dashboard')}
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold text-xs tracking-wider transition shadow-lg shadow-red-950 flex items-center gap-2"
              >
                <span>Return to Workbench ({user.name})</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <>
                <button
                  onClick={() => scrollToAuth('demo')}
                  className="px-3.5 py-1.5 rounded-lg bg-red-600/90 hover:bg-red-500 text-white font-semibold text-xs tracking-wide transition shadow-md shadow-red-950"
                >
                  Try the live demo
                </button>
                <button
                  onClick={() => scrollToAuth('official')}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/80 font-semibold text-xs tracking-wide transition"
                >
                  Official sign-in
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-slate-800/80 py-16 lg:py-24">
        {/* Leaflet non-interactive backdrop */}
        <MapBackdrop 
          interactive={false} 
          className="absolute inset-0 opacity-25 filter grayscale contrast-125 pointer-events-none" 
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#07080a]/90 via-[#07080a]/75 to-[#07080a] pointer-events-none" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 grid lg:grid-cols-12 gap-12 items-center z-10">
          {/* Hero Left Content */}
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-950/60 border border-red-800/50 text-[11px] font-mono text-red-300">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
              <span>CASE SP-014 ACTIVE SURVEILLANCE MATRIX</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-white leading-tight">
              Evidence-defensible criminal network intelligence
            </h1>

            <div className="p-4 rounded-xl bg-slate-950/80 border-l-4 border-l-red-500 border border-slate-800/90 shadow-xl backdrop-blur-sm">
              <p className="text-base sm:text-lg font-medium text-slate-200 italic leading-relaxed">
                "Five girls vanished in 24 hours. The data was in five different places."
              </p>
              <div className="mt-2 text-xs font-mono text-slate-400">
                Pattern matching across CDR, UPI dumps, FIRs, and tower telemetry with verifiable chain of custody.
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                onClick={() => scrollToAuth('demo')}
                className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-bold text-sm uppercase tracking-wider transition shadow-xl shadow-red-950/80 flex items-center gap-2.5 border border-red-500/50"
              >
                <span>Try the live demo</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                onClick={() => scrollToAuth('official')}
                className="px-6 py-3.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-200 hover:text-white font-bold text-sm uppercase tracking-wider transition border border-slate-700 flex items-center gap-2"
              >
                <Lock className="w-4 h-4 text-slate-400" />
                <span>Official sign-in</span>
              </button>
            </div>

            {/* Evidence chips */}
            <div className="pt-4 flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-400">
              <span className="text-slate-500 uppercase font-semibold">Evidence Chips:</span>
              <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-red-300/90">[EVD-REF-01]</span>
              <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">[FIR-07-S3]</span>
              <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">[TWR-KUM-04]</span>
              <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">[SHA256: 65B-INTACT]</span>
            </div>
          </div>

          {/* Hero Right: Sign-in Card */}
          <div ref={authSectionRef} className="lg:col-span-5">
            <div className="bg-slate-900/95 border border-slate-800/90 rounded-2xl p-6 sm:p-7 shadow-2xl backdrop-blur-xl relative">
              <div className="absolute top-0 right-0 -mr-2 -mt-2 w-24 h-24 bg-red-600/10 rounded-full blur-2xl pointer-events-none"></div>

              {/* Tab Selector */}
              <div className="grid grid-cols-2 p-1 bg-slate-950 rounded-xl border border-slate-800 mb-6">
                <button
                  type="button"
                  onClick={() => { setActiveTab('demo'); setDemoError(''); }}
                  className={`py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                    activeTab === 'demo'
                      ? 'bg-red-600 text-white shadow-md shadow-red-950'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <UserCheck className="w-3.5 h-3.5" />
                  <span>Demo sandbox (no MFA)</span>
                </button>
                <button
                  type="button"
                  onClick={() => { setActiveTab('official'); setOfficialError(''); }}
                  className={`py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                    activeTab === 'official'
                      ? 'bg-red-600 text-white shadow-md shadow-red-950'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Lock className="w-3.5 h-3.5" />
                  <span>Official Sign-In</span>
                </button>
              </div>

              {/* Tab 1: Try Live Demo */}
              {activeTab === 'demo' && (
                <div>
                  <div className="mb-4">
                    <h3 className="text-base font-bold text-white">Instant Demo Access</h3>
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                      Explore the live operational workbench with synthetic police case data.
                    </p>
                  </div>

                  {demoError && (
                    <div className="mb-4 p-3 bg-red-950/60 border border-red-800 rounded-lg text-xs text-red-200 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                      <span>{demoError}</span>
                    </div>
                  )}

                  {demoNoticeStatus && (
                    <div className="mb-4 p-2.5 bg-amber-950/50 border border-amber-800/80 rounded-lg text-xs text-amber-300 font-mono flex items-center gap-2">
                      <Info className="w-4 h-4 text-amber-400 flex-shrink-0" />
                      <span>{demoNoticeStatus}</span>
                    </div>
                  )}

                  <form onSubmit={handleDemoSubmit} className="space-y-4">
                    {/* Honeypot field - invisible to human users */}
                    <div className="opacity-0 absolute -left-[9999px] h-0 w-0 overflow-hidden" aria-hidden="true">
                      <label htmlFor="website-field">Leave blank</label>
                      <input 
                        id="website-field"
                        type="text" 
                        name="website" 
                        tabIndex={-1} 
                        value={honeypot} 
                        onChange={(e) => setHoneypot(e.target.value)} 
                        autoComplete="off" 
                      />
                    </div>

                    <div>
                      <label className="text-xs font-medium text-slate-300 block mb-1">Your Name</label>
                      <input
                        type="text"
                        value={demoName}
                        onChange={(e) => setDemoName(e.target.value)}
                        placeholder="e.g. Officer Sharma"
                        required
                        className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-red-500 transition font-sans"
                      />
                    </div>

                    <div>
                      <label className="text-xs font-medium text-slate-300 block mb-1">Email Address</label>
                      <div className="relative">
                        <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                        <input
                          type="email"
                          value={demoEmail}
                          onChange={(e) => setDemoEmail(e.target.value)}
                          placeholder="officer@agency.org"
                          required
                          className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-red-500 transition font-mono"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="text-xs font-medium text-slate-300 block mb-1">Simulated Role</label>
                      <select
                        value={demoRole}
                        onChange={(e) => setDemoRole(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-red-500 transition font-sans"
                      >
                        <option value="SP / DySP">SP / DySP (Full Access & Unmasking)</option>
                        <option value="Cyber Cell Analyst">Cyber Cell Analyst (Graph & Ledger)</option>
                        <option value="Head Constable">Head Constable (Propose Merges)</option>
                        <option value="Constable">Constable (Masked Phone Numbers)</option>
                      </select>
                    </div>

                    <p className="text-[11px] text-slate-400 bg-slate-950/80 p-2.5 rounded-lg border border-slate-800/80 leading-relaxed font-sans">
                      We store only the name and email you enter, to personalise this demo and send one login notice. Synthetic data only. Delete on request.
                    </p>

                    <button
                      type="submit"
                      disabled={demoLoading}
                      className="w-full py-2.5 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-bold rounded-lg text-xs uppercase tracking-wider transition flex items-center justify-center gap-2 shadow-lg shadow-red-950 border border-red-500/40 disabled:opacity-50"
                    >
                      {demoLoading ? 'Starting Session...' : (
                        <>
                          <span>Launch Live Demo Workbench</span>
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </form>
                </div>
              )}

              {/* Tab 2: Official Sign-in */}
              {activeTab === 'official' && (
                <div>
                  <div className="mb-4">
                    <h3 className="text-base font-bold text-white">Investigator Credentials</h3>
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                      Sign in with seeded departmental credentials or use one-click autofill below.
                    </p>
                  </div>

                  {officialError && (
                    <div className="mb-4 p-3 bg-red-950/60 border border-red-800 rounded-lg text-xs text-red-200 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                      <span>{officialError}</span>
                    </div>
                  )}

                  {mfaChallenge ? (
                    <form onSubmit={handleOfficialSubmit} className="space-y-4">
                      {/* Officer Identity & Protocol Banner */}
                      <div className="p-3 bg-red-950/40 border border-red-800/60 rounded-xl flex items-center justify-between">
                        <div>
                          <div className="text-[10px] font-mono uppercase tracking-wider text-red-400 font-bold flex items-center gap-1.5">
                            <Shield className="w-3.5 h-3.5" />
                            <span>Two-Factor Authentication</span>
                          </div>
                          <div className="text-xs font-semibold text-slate-100 mt-0.5">
                            {mfaChallenge.name || officialEmail}
                          </div>
                        </div>
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-red-900/60 text-red-300 border border-red-700/50">
                          {mfaChallenge.role ? mfaChallenge.role.replace('_', ' ') : 'Investigator'}
                        </span>
                      </div>

                      {/* Mode Switcher Tabs */}
                      <div className="flex items-center justify-center gap-1.5 p-1 bg-slate-950 rounded-lg border border-slate-800 text-[11px]">
                        <button
                          type="button"
                          onClick={() => setQrMode('camera')}
                          className={`flex-1 py-1.5 px-2.5 rounded-md transition font-medium flex items-center justify-center gap-1.5 ${
                            qrMode === 'camera'
                              ? 'bg-red-600 text-white shadow-md'
                              : 'text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          <Smartphone className="w-3.5 h-3.5" />
                          <span>Phone Camera (Direct Code)</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setQrMode('authenticator')}
                          className={`flex-1 py-1.5 px-2.5 rounded-md transition font-medium flex items-center justify-center gap-1.5 ${
                            qrMode === 'authenticator'
                              ? 'bg-red-600 text-white shadow-md'
                              : 'text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          <QrCode className="w-3.5 h-3.5" />
                          <span>Authenticator App</span>
                        </button>
                      </div>

                      {/* Instruction Callout */}
                      <div className="text-center px-1">
                        <p className="text-xs text-slate-300 font-medium leading-relaxed">
                          {qrMode === 'camera' ? (
                            <>
                              Scan the QR code below with your <strong className="text-white">phone camera</strong>. It will display a <strong className="text-amber-300">6-digit code</strong> to sign in.
                            </>
                          ) : (
                            <>
                              Scan below in <strong className="text-white">Google Authenticator</strong> or Microsoft Authenticator to generate your 6-digit code.
                            </>
                          )}
                        </p>
                      </div>

                      {/* Prominent High-Tech QR Code Frame */}
                      <div className="text-center py-4 px-2 bg-slate-950 rounded-2xl border border-slate-800 shadow-xl">
                        <div className="relative inline-block bg-white p-3 rounded-xl shadow-2xl shadow-red-950/60 border-2 border-red-500/30">
                          {/* Tech corner accents */}
                          <div className="absolute -top-1 -left-1 w-3.5 h-3.5 border-t-2 border-l-2 border-red-500"></div>
                          <div className="absolute -top-1 -right-1 w-3.5 h-3.5 border-t-2 border-r-2 border-red-500"></div>
                          <div className="absolute -bottom-1 -left-1 w-3.5 h-3.5 border-b-2 border-l-2 border-red-500"></div>
                          <div className="absolute -bottom-1 -right-1 w-3.5 h-3.5 border-b-2 border-r-2 border-red-500"></div>

                          {mfaChallenge.qr_code ? (
                            <img
                              src={qrMode === 'authenticator' && mfaChallenge.qr_code_auth ? mfaChallenge.qr_code_auth : mfaChallenge.qr_code}
                              alt="SAKSHI Official 6-Digit MFA QR Code"
                              className="w-40 h-40 object-contain block mx-auto"
                            />
                          ) : (
                            <div className="w-40 h-40 flex items-center justify-center text-xs text-slate-500">
                              Generating QR...
                            </div>
                          )}
                        </div>

                        {/* Timer & Refresh Controls */}
                        <div className="mt-3 flex items-center justify-between max-w-[210px] mx-auto text-[11px] font-mono text-slate-400">
                          <div className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                            <span>Valid: <strong className="text-emerald-300">{timeLeft}s</strong></span>
                          </div>
                          <button
                            type="button"
                            onClick={handleRefreshCode}
                            disabled={refreshingMfa}
                            className="text-[11px] text-slate-400 hover:text-red-300 flex items-center gap-1 transition"
                            title="Generate fresh QR code"
                          >
                            <RefreshCw className={`w-3 h-3 ${refreshingMfa ? 'animate-spin' : ''}`} />
                            <span>Refresh</span>
                          </button>
                        </div>
                      </div>

                      {/* Quick Code Autofill Pill (Presenter & Testing Convenience) */}
                      {mfaChallenge.current_code && (
                        <button
                          type="button"
                          onClick={() => {
                            setTotpCode(mfaChallenge.current_code);
                            setCodeCopied(true);
                            setTimeout(() => setCodeCopied(false), 2000);
                          }}
                          className="w-full py-1.5 px-3 rounded-lg bg-slate-950/90 border border-dashed border-red-500/40 hover:border-red-500 text-[11px] text-slate-300 hover:text-white transition flex items-center justify-between shadow-sm"
                        >
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] uppercase font-mono text-slate-500">Code from scan:</span>
                            <span className="font-mono font-bold text-amber-300 tracking-widest">{mfaChallenge.current_code}</span>
                          </div>
                          <span className="text-[10px] text-red-400 font-semibold flex items-center gap-1">
                            {codeCopied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                            <span>{codeCopied ? 'Filled in!' : 'Click to autofill'}</span>
                          </span>
                        </button>
                      )}

                      {/* 6-Digit Code Input */}
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-xs font-medium text-slate-300">
                            Enter 6-Digit Code
                          </label>
                          <span className="text-[10px] font-mono text-slate-400">
                            From phone scan
                          </span>
                        </div>
                        <input
                          type="text"
                          maxLength={6}
                          value={totpCode}
                          onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                          placeholder="••••••"
                          required
                          autoFocus
                          className="w-full text-center text-2xl tracking-[0.4em] font-mono font-bold py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-red-500 transition shadow-inner"
                        />
                      </div>

                      {/* Submit & Cancel */}
                      <button
                        type="submit"
                        disabled={officialLoading || totpCode.length < 6}
                        className="w-full py-2.5 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-bold rounded-lg text-xs uppercase tracking-wider transition flex items-center justify-center gap-2 shadow-lg shadow-red-950 border border-red-500/40 disabled:opacity-50"
                      >
                        {officialLoading ? 'Verifying...' : (
                          <>
                            <span>Verify Code & Sign In</span>
                            <ArrowRight className="w-4 h-4" />
                          </>
                        )}
                      </button>

                      <div className="text-center pt-1">
                        <button
                          type="button"
                          onClick={() => { setMfaChallenge(null); setTotpCode(''); }}
                          className="text-[11px] text-slate-400 hover:text-slate-200 underline"
                        >
                          Cancel / Back to Password
                        </button>
                      </div>
                    </form>
                  ) : (
                    <form onSubmit={handleOfficialSubmit} className="space-y-4">
                      <div>
                        <label className="text-xs font-medium text-slate-300 block mb-1">Official Email</label>
                        <div className="relative">
                          <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                          <input
                            type="email"
                            value={officialEmail}
                            onChange={(e) => setOfficialEmail(e.target.value)}
                            required
                            className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-red-500 transition font-mono"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="text-xs font-medium text-slate-300 block mb-1">Passcode</label>
                        <div className="relative">
                          <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                          <input
                            type="password"
                            value={officialPassword}
                            onChange={(e) => setOfficialPassword(e.target.value)}
                            required
                            className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-red-500 transition font-mono"
                          />
                        </div>
                      </div>

                      <button
                        type="submit"
                        disabled={officialLoading}
                        className="w-full py-2.5 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-bold rounded-lg text-xs uppercase tracking-wider transition flex items-center justify-center gap-2 shadow-lg shadow-red-950 border border-red-500/40 disabled:opacity-50"
                      >
                        {officialLoading ? 'Verifying...' : (
                          <>
                            <span>Initialize Official Session</span>
                            <ArrowRight className="w-4 h-4" />
                          </>
                        )}
                      </button>
                    </form>
                  )}

                  {/* Seeded Accounts Autofill */}
                  <div className="mt-5 pt-4 border-t border-slate-800">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-mono uppercase text-slate-400 font-bold">
                        Seeded Test Accounts
                      </span>
                      <span className="text-[10px] font-mono text-amber-400">pwd: demo123</span>
                    </div>
                    <div className="grid grid-cols-1 gap-1.5 max-h-40 overflow-y-auto pr-1">
                      {SEED_USERS.map((seed) => (
                        <button
                          key={seed.email}
                          type="button"
                          onClick={() => autofillOfficial(seed)}
                          className={`text-left px-2.5 py-1.5 rounded-lg border text-xs transition flex items-center justify-between ${
                            officialEmail === seed.email
                              ? 'bg-red-950/50 border-red-500/50 text-red-200'
                              : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                          }`}
                        >
                          <div>
                            <div className="font-semibold text-slate-200 text-[11px]">{seed.name}</div>
                            <div className="text-[9px] font-mono text-slate-400">{seed.email}</div>
                          </div>
                          <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-red-300">
                            {seed.role.replace('_', ' ')}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Live Counters Strip */}
      <section className="bg-slate-950 border-b border-slate-800/80 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-red-500" />
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400 font-bold">
                Live Case Telemetry (Public Aggregates)
              </span>
            </div>
            <span className="text-[10px] font-mono text-slate-500">
              Zero PII Exposed • Synchronized with sakshi.db
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/90 shadow-md">
              <div className="text-[11px] font-mono text-slate-400 uppercase">Resolved Entities</div>
              <div className="text-2xl sm:text-3xl font-black font-mono text-white mt-1">
                {summary.entities}
              </div>
              <div className="text-[10px] text-slate-500 mt-1 font-mono">Linked person & vehicle nodes</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/90 shadow-md">
              <div className="text-[11px] font-mono text-slate-400 uppercase">Call Detail Records</div>
              <div className="text-2xl sm:text-3xl font-black font-mono text-white mt-1">
                {summary.calls}
              </div>
              <div className="text-[10px] text-slate-500 mt-1 font-mono">Inter-cell interactions analyzed</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/90 shadow-md">
              <div className="text-[11px] font-mono text-slate-400 uppercase">Financial Transactions</div>
              <div className="text-2xl sm:text-3xl font-black font-mono text-white mt-1">
                {summary.transactions}
              </div>
              <div className="text-[10px] text-slate-500 mt-1 font-mono">Pass-through UPI & cash structuring</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/90 shadow-md">
              <div className="text-[11px] font-mono text-slate-400 uppercase">Active Alerts</div>
              <div className="text-2xl sm:text-3xl font-black font-mono text-red-400 mt-1">
                {summary.alerts}
              </div>
              <div className="text-[10px] text-slate-500 mt-1 font-mono">Golden-hour & co-movement flags</div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works (4 Steps) */}
      <section className="py-16 border-b border-slate-800/80 bg-[#07080a]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] font-mono text-red-400 uppercase">
              Pipeline Architecture
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white mt-3">
              How SAKSHI Connects Disconnected Clues
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-2">
              From disparate tower dumps to court-admissible Section 65B dossiers in four deterministic phases.
            </p>
          </div>

          <div className="grid md:grid-cols-4 gap-6">
            <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800 hover:border-red-900/60 transition group">
              <div className="w-9 h-9 rounded-lg bg-red-950/80 border border-red-800/60 text-red-400 flex items-center justify-center font-mono font-bold text-sm mb-4">
                01
              </div>
              <h3 className="text-sm font-bold text-white group-hover:text-red-300 transition">Ingest</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Raw CDR logs, UPI transaction slips, FIR witness statements, and tower dumps are parsed into canonical evidentiary records with SHA-256 row hashes.
              </p>
              <div className="mt-3 text-[10px] font-mono text-slate-500">[Ingest: 1,083 Records]</div>
            </div>

            <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800 hover:border-red-900/60 transition group">
              <div className="w-9 h-9 rounded-lg bg-red-950/80 border border-red-800/60 text-red-400 flex items-center justify-center font-mono font-bold text-sm mb-4">
                02
              </div>
              <h3 className="text-sm font-bold text-white group-hover:text-red-300 transition">Resolve Identities</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Deterministic and fuzzy matchers cluster shared IMEIs, account numbers, and phonetic aliases into unified entities with human-in-the-loop review.
              </p>
              <div className="mt-3 text-[10px] font-mono text-slate-500">[Jaro-Winkler & Token Set]</div>
            </div>

            <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800 hover:border-red-900/60 transition group">
              <div className="w-9 h-9 rounded-lg bg-red-950/80 border border-red-800/60 text-red-400 flex items-center justify-center font-mono font-bold text-sm mb-4">
                03
              </div>
              <h3 className="text-sm font-bold text-white group-hover:text-red-300 transition">Score & Alert</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Betweenness centrality, co-movement velocities, burner handoff patterns, and pass-through financial structurings automatically trigger weighted investigative alerts.
              </p>
              <div className="mt-3 text-[10px] font-mono text-slate-500">[Golden-Hour Proximity Engine]</div>
            </div>

            <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800 hover:border-red-900/60 transition group">
              <div className="w-9 h-9 rounded-lg bg-red-950/80 border border-red-800/60 text-red-400 flex items-center justify-center font-mono font-bold text-sm mb-4">
                04
              </div>
              <h3 className="text-sm font-bold text-white group-hover:text-red-300 transition">Explain with Evidence</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Every edge in the network decomposes into verifiable evidence snippets. Zero hallucination; every graph link points to an exact evidentiary citation.
              </p>
              <div className="mt-3 text-[10px] font-mono text-slate-500">[Section 65B Hash Chain]</div>
            </div>
          </div>
        </div>
      </section>

      {/* 6 Feature Cards */}
      <section className="py-16 border-b border-slate-800/80 bg-slate-950">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] font-mono text-red-400 uppercase">
              Core Capabilities
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white mt-3">
              Purpose-Built for Evidence Defense
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-2">
              Every analytical feature provides cryptographic defensibility for court scrutiny.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* 1. Explainable links */}
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/90 hover:border-red-800/60 transition">
              <div className="w-10 h-10 rounded-lg bg-red-950/70 border border-red-800/50 flex items-center justify-center text-red-400 mb-4">
                <Network className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-white">Explainable Links</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Click any edge in the graph to see its complete mathematical breakdown: call frequency, co-location confidence, and financial pass-through weights.
              </p>
              <div className="mt-3 pt-3 border-t border-slate-800/60 text-[10px] font-mono text-slate-500">
                Formula: 1 - ∏(1 - wᵢ · sᵢ)
              </div>
            </div>

            {/* 2. Inspectable merges */}
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/90 hover:border-red-800/60 transition">
              <div className="w-10 h-10 rounded-lg bg-red-950/70 border border-red-800/50 flex items-center justify-center text-red-400 mb-4">
                <GitMerge className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-white">Inspectable Merges</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Side-by-side entity candidate diffs showing matching and conflicting tokens. Approvals require SP authorization; mistakes can be unmerged with 1 click.
              </p>
              <div className="mt-3 pt-3 border-t border-slate-800/60 text-[10px] font-mono text-slate-500">
                Clamped confidence 0-100%
              </div>
            </div>

            {/* 3. Time-travel and cut */}
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/90 hover:border-red-800/60 transition">
              <div className="w-10 h-10 rounded-lg bg-red-950/70 border border-red-800/50 flex items-center justify-center text-red-400 mb-4">
                <Clock className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-white">Time-Travel & Cut</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Replay network topology day-by-day. Run interdiction simulations to remove critical key brokers and measure graph fragmentation percentage.
              </p>
              <div className="mt-3 pt-3 border-t border-slate-800/60 text-[10px] font-mono text-slate-500">
                Betweenness delta calculation
              </div>
            </div>

            {/* 4. Golden-hour alert */}
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/90 hover:border-red-800/60 transition">
              <div className="w-10 h-10 rounded-lg bg-red-950/70 border border-red-800/50 flex items-center justify-center text-red-400 mb-4">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-white">Golden-Hour Alert</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                First 48-hour geospatial tracker pinpointing burner handset activations, victim handoffs, and transit corridors along National Highway 53.
              </p>
              <div className="mt-3 pt-3 border-t border-slate-800/60 text-[10px] font-mono text-slate-500">
                Haversine co-movement window
              </div>
            </div>

            {/* 5. Tamper-evident ledger */}
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/90 hover:border-red-800/60 transition">
              <div className="w-10 h-10 rounded-lg bg-red-950/70 border border-red-800/50 flex items-center justify-center text-red-400 mb-4">
                <Fingerprint className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-white">Tamper-Evident Ledger</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Every merge, note, unmasking, or export appends to a cryptographic SHA-256 forward-linked block. Any out-of-band DB mutation immediately flags red.
              </p>
              <div className="mt-3 pt-3 border-t border-slate-800/60 text-[10px] font-mono text-slate-500">
                Section 65B Indian Evidence Act compliant
              </div>
            </div>

            {/* 6. Cited copilot */}
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/90 hover:border-red-800/60 transition">
              <div className="w-10 h-10 rounded-lg bg-red-950/70 border border-red-800/50 flex items-center justify-center text-red-400 mb-4">
                <Search className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-white">Cited Copilot</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Natural-language query engine executing direct SQL tools. Every factual assertion includes verified case citations; out-of-scope queries return exact negative responses.
              </p>
              <div className="mt-3 pt-3 border-t border-slate-800/60 text-[10px] font-mono text-slate-500">
                Strict database ground-truth guardrails
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Responsible AI Strip */}
      <section className="bg-slate-900/40 border-b border-slate-800/80 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
              Responsible AI & Defensibility Commitments
            </span>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800/80">
              <div className="font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Patterns for Investigator Review</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Algorithms surface statistical leads and patterns; they never make accusations or determine guilt.
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800/80">
              <div className="font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Human Approval</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Entity merges, warrants, and investigative actions strictly require officer confirmation on the record.
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800/80">
              <div className="font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Masked Roles (RBAC)</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Field constables see masked phone numbers and operational directives; raw telemetry requires SP privileges.
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800/80">
              <div className="font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Synthetic Data Only</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                All names, phone numbers, IMEI records, and financial identifiers are purely fictional simulations.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Mandatory Persistent Footer Banner */}
      <footer className="py-6 bg-[#07080a] text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-2">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs text-amber-300 font-medium shadow-sm">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
            <span>Synthetic data. Patterns for investigator review. Not an accusation.</span>
          </div>
          <div className="text-[11px] text-slate-500 font-mono">
            SAKSHI Case Intelligence Platform • State Police Cyber Cell Benchmarking Environment
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
