import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Shield, 
  Lock, 
  Mail, 
  ArrowRight, 
  AlertCircle, 
  QrCode, 
  Smartphone, 
  RefreshCw, 
  Copy, 
  Check 
} from 'lucide-react';
import QRCode from 'qrcode';
import { useAuth, SEED_USERS } from '../context/AuthContext';
import { refreshMfaApi } from '../api';

export const Login = () => {
  const [email, setEmail] = useState('spdysp@demo.in');
  const [password, setPassword] = useState('demo123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mfaChallenge, setMfaChallenge] = useState(null);
  const [totpCode, setTotpCode] = useState('');
  const [qrMode, setQrMode] = useState('camera'); // 'camera' | 'authenticator'
  const [timeLeft, setTimeLeft] = useState(30);
  const [codeCopied, setCodeCopied] = useState(false);
  const [refreshingMfa, setRefreshingMfa] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  // Live TOTP countdown and auto-refresh when on MFA challenge
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
      const res = await refreshMfaApi(mfaChallenge.email || email);
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
          `otpauth://totp/SAKSHI:${encodeURIComponent(email)}?secret=${mfaChallenge.secret || 'JBSWY3DPEHPK3PXP'}&issuer=SAKSHI`,
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

  const handleLogin = async (e) => {
    if (e) e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await login(email, password, totpCode || null);
      if (res && res.mfa_required) {
        setMfaChallenge(res);
        if (res.expires_in) setTimeLeft(res.expires_in);
        setLoading(false);
        return;
      }
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const autofill = (demoUser) => {
    setEmail(demoUser.email);
    setPassword('demo123');
    setMfaChallenge(null);
    setTotpCode('');
    setTimeLeft(30);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-between p-4 sm:p-8 font-sans">
      {/* Background visual accents */}
      <div className="fixed inset-0 pointer-events-none opacity-20 bg-[radial-gradient(#14b8a6_1px,transparent_1px)] [background-size:24px_24px]"></div>

      {/* Header */}
      <div className="flex items-center justify-between max-w-5xl mx-auto w-full z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-teal-800 flex items-center justify-center font-black text-slate-950 text-xl shadow-lg shadow-teal-900/50">
            सा
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-wider text-slate-100 flex items-center gap-2">
              SAKSHI
              <span className="text-xs px-2 py-0.5 rounded bg-teal-500/10 text-teal-300 border border-teal-500/30 font-mono font-medium">
                PROTOTYPE
              </span>
            </h1>
            <p className="text-xs text-slate-400">Evidence-Defensible Criminal Network Intelligence Workbench</p>
          </div>
        </div>
        <div className="text-right hidden sm:block">
          <div className="text-xs font-mono text-slate-400">STATE POLICE CYBER CELL</div>
          <div className="text-[10px] text-teal-400">SECURE INVESTIGATIVE VAULT</div>
        </div>
      </div>

      {/* Main Login Card */}
      <div className="max-w-md w-full mx-auto z-10 my-8">
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl backdrop-blur-md">
          <div className="mb-6">
            <h2 className="text-lg font-bold text-slate-100">Investigator Access</h2>
            <p className="text-xs text-slate-400 mt-1">
              Sign in with institutional credentials to access case dossiers and analytical graphs.
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-rose-950/50 border border-rose-800/80 rounded-lg flex items-center gap-2.5 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {mfaChallenge ? (
            <form onSubmit={handleLogin} className="space-y-4">
              {/* Officer Identity & Protocol Banner */}
              <div className="p-3 bg-teal-950/40 border border-teal-800/60 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-wider text-teal-400 font-bold flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5" />
                    <span>Two-Factor Authentication</span>
                  </div>
                  <div className="text-xs font-semibold text-slate-100 mt-0.5">
                    {mfaChallenge.name || email}
                  </div>
                </div>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-teal-900/60 text-teal-300 border border-teal-700/50">
                  {mfaChallenge.role ? mfaChallenge.role.replace('_', ' ') : 'Official'}
                </span>
              </div>

              {/* Mode Switcher Tabs */}
              <div className="flex items-center justify-center gap-1.5 p-1 bg-slate-950 rounded-lg border border-slate-800 text-[11px]">
                <button
                  type="button"
                  onClick={() => setQrMode('camera')}
                  className={`flex-1 py-1.5 px-2.5 rounded-md transition font-medium flex items-center justify-center gap-1.5 ${
                    qrMode === 'camera'
                      ? 'bg-teal-600 text-slate-950 font-bold shadow-md'
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
                      ? 'bg-teal-600 text-slate-950 font-bold shadow-md'
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
                      Scan the QR code below with your <strong className="text-white">phone camera</strong>. It will display a <strong className="text-teal-300">6-digit code</strong> to sign in.
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
                <div className="relative inline-block bg-white p-3 rounded-xl shadow-2xl shadow-teal-950/60 border-2 border-teal-500/30">
                  <div className="absolute -top-1 -left-1 w-3.5 h-3.5 border-t-2 border-l-2 border-teal-500"></div>
                  <div className="absolute -top-1 -right-1 w-3.5 h-3.5 border-t-2 border-r-2 border-teal-500"></div>
                  <div className="absolute -bottom-1 -left-1 w-3.5 h-3.5 border-b-2 border-l-2 border-teal-500"></div>
                  <div className="absolute -bottom-1 -right-1 w-3.5 h-3.5 border-b-2 border-r-2 border-teal-500"></div>

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
                    <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse"></span>
                    <span>Valid: <strong className="text-teal-300">{timeLeft}s</strong></span>
                  </div>
                  <button
                    type="button"
                    onClick={handleRefreshCode}
                    disabled={refreshingMfa}
                    className="text-[11px] text-slate-400 hover:text-teal-300 flex items-center gap-1 transition"
                    title="Generate fresh QR code"
                  >
                    <RefreshCw className={`w-3 h-3 ${refreshingMfa ? 'animate-spin' : ''}`} />
                    <span>Refresh</span>
                  </button>
                </div>
              </div>

              {/* Quick Code Autofill Pill */}
              {mfaChallenge.current_code && (
                <button
                  type="button"
                  onClick={() => {
                    setTotpCode(mfaChallenge.current_code);
                    setCodeCopied(true);
                    setTimeout(() => setCodeCopied(false), 2000);
                  }}
                  className="w-full py-1.5 px-3 rounded-lg bg-slate-950/90 border border-dashed border-teal-500/40 hover:border-teal-500 text-[11px] text-slate-300 hover:text-white transition flex items-center justify-between shadow-sm"
                >
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] uppercase font-mono text-slate-500">Code from scan:</span>
                    <span className="font-mono font-bold text-teal-300 tracking-widest">{mfaChallenge.current_code}</span>
                  </div>
                  <span className="text-[10px] text-teal-400 font-semibold flex items-center gap-1">
                    {codeCopied ? <Check className="w-3 h-3 text-teal-300" /> : <Copy className="w-3 h-3" />}
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
                  className="w-full text-center text-2xl tracking-[0.4em] font-mono font-bold py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-teal-500 transition shadow-inner"
                />
              </div>

              {/* Submit & Cancel */}
              <button
                type="submit"
                disabled={loading || totpCode.length < 6}
                className="w-full py-2.5 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-500 hover:to-teal-400 text-slate-950 font-bold rounded-lg text-xs uppercase tracking-wider transition flex items-center justify-center gap-2 shadow-lg shadow-teal-950/60 disabled:opacity-50"
              >
                {loading ? 'Verifying...' : (
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
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">Official Email ID</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="investigator@demo.in"
                    required
                    className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-teal-500 transition font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">Security Passcode</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-teal-500 transition font-mono"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-500 hover:to-teal-400 text-slate-950 font-bold rounded-lg text-xs uppercase tracking-wider transition flex items-center justify-center gap-2 shadow-lg shadow-teal-950/60 disabled:opacity-50"
              >
                {loading ? 'Authenticating...' : (
                  <>
                    <span>Initialize Workbench</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Quick Demo Accounts Chips */}
          <div className="mt-6 pt-5 border-t border-slate-800">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Demo Accounts (Click to Autofill)
              </span>
              <span className="text-[10px] font-mono text-amber-400/90">pwd: demo123</span>
            </div>
            <div className="grid grid-cols-1 gap-1.5">
              {SEED_USERS.map((u) => {
                const isSelected = email === u.email;
                return (
                  <button
                    key={u.email}
                    type="button"
                    onClick={() => autofill(u)}
                    className={`text-left px-3 py-2 rounded-lg border text-xs transition flex items-center justify-between ${
                      isSelected
                        ? 'bg-teal-950/50 border-teal-500/50 text-teal-200'
                        : 'bg-slate-950/70 border-slate-800/80 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                    }`}
                  >
                    <div>
                      <div className="font-semibold text-slate-200">{u.name}</div>
                      <div className="text-[10px] font-mono text-slate-400">{u.email}</div>
                    </div>
                    <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-teal-300">
                      {u.role.replace('_', ' ')}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Mandatory Persistent Footer Banner */}
      <div className="text-center z-10 py-2">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs text-amber-300/90 font-medium shadow-md">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
          <span>Synthetic data. Patterns for investigator review. Not an accusation.</span>
        </div>
      </div>
    </div>
  );
};

export default Login;
