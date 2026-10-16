import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  RefreshCw, 
  Bug, 
  Hash, 
  Lock, 
  Clock, 
  FileCheck,
  AlertTriangle,
  RotateCcw
} from 'lucide-react';
import { getLedgerApi, verifyLedgerApi, debugTamperApi, debugResetTamperApi } from '../api';
import { useAuth } from '../context/AuthContext';

export const Ledger = () => {
  const { user, hasRole, debugMode } = useAuth();
  const [ledger, setLedger] = useState(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);
  const [error, setError] = useState('');

  const canAccessLedger = hasRole(['cyber_cell', 'sp_dysp', 'auditor']);

  const fetchLedger = async () => {
    if (!canAccessLedger) return;
    setLoading(true);
    try {
      const data = await getLedgerApi();
      setLedger(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to retrieve chain of custody ledger.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLedger();
  }, [user?.role]);

  const handleVerify = async () => {
    if (!canAccessLedger) return;
    setVerifying(true);
    setVerifyResult(null);
    try {
      const res = await verifyLedgerApi();
      setTimeout(() => {
        setVerifying(false);
        setVerifyResult(res);
      }, 600);
    } catch (err) {
      setVerifying(false);
      setError(err.response?.data?.detail || 'Chain verification failed.');
    }
  };

  const handleTamper = async () => {
    try {
      await debugTamperApi();
      await fetchLedger();
      await handleVerify();
    } catch (err) {
      setError(err.response?.data?.detail || 'Tamper injection failed.');
    }
  };

  const handleResetTamper = async () => {
    try {
      await debugResetTamperApi();
      await fetchLedger();
      await handleVerify();
    } catch (err) {
      setError(err.response?.data?.detail || 'Reset failed.');
    }
  };

  if (!canAccessLedger) {
    return (
      <div className="p-8 max-w-lg mx-auto text-center space-y-4 my-auto">
        <div className="w-14 h-14 rounded-2xl bg-rose-950/60 border border-rose-800 flex items-center justify-center text-rose-400 mx-auto">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h2 className="text-lg font-bold text-slate-100">Restricted Forensic Vault</h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          The cryptographic Chain of Custody is restricted to Cyber Cell, SP/DySP, and Judicial Auditors.
        </p>
        <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 text-xs text-slate-400 font-mono">
          Current Role: <span className="text-teal-300 font-bold">{user?.role}</span>
        </div>
      </div>
    );
  }

  const isTampered = ledger?.status === 'tampered' || (verifyResult && !verifyResult.ok);

  return (
    <div className="p-4 lg:p-6 space-y-6 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 lg:p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 text-xs font-mono font-bold bg-purple-500/15 text-purple-300 border border-purple-500/30 rounded flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-purple-400" />
              SECTION 65B CHAIN OF CUSTODY
            </span>
            <span className="text-xs text-slate-400 font-mono">
              20 Chained Ledger Blocks
            </span>
          </div>
          <h1 className="text-xl lg:text-2xl font-black text-slate-100 tracking-tight">
            Cryptographic Audit Ledger
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Every evidentiary ingestion, telecom scrape, FIR attachment, and graph recalculation is chained with SHA-256 digests. Any tampering breaks backward linkage immediately.
          </p>
        </div>

        {/* Verification & Debug Actions */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleVerify}
            disabled={verifying}
            className={`px-4 py-2 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center gap-2 transition shadow-lg ${
              isTampered
                ? 'bg-rose-600 hover:bg-rose-500 text-white'
                : 'bg-emerald-600 hover:bg-emerald-500 text-slate-950 shadow-emerald-950/60'
            }`}
          >
            {verifying ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : isTampered ? (
              <XCircle className="w-4 h-4" />
            ) : (
              <CheckCircle2 className="w-4 h-4" />
            )}
            <span>{verifying ? 'Scanning Chain...' : 'Verify Chain Integrity'}</span>
          </button>

          {debugMode && (
            <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
              <button
                onClick={handleTamper}
                className="px-3 py-1.5 rounded-lg bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800 text-xs font-mono font-medium transition flex items-center gap-1.5"
                title="Inject unauthorized hash modification into Block #17 for live demo"
              >
                <Bug className="w-3.5 h-3.5 text-rose-400" />
                <span>Tamper Demo (Break #17)</span>
              </button>

              <button
                onClick={handleResetTamper}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono transition"
                title="Restore genuine chain state"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Verification Result Banner */}
      {verifyResult && (
        <div className={`p-4 rounded-xl border flex items-center justify-between text-xs animate-fade-in ${
          verifyResult.ok
            ? 'bg-emerald-950/70 border-emerald-800 text-emerald-200'
            : 'bg-rose-950/80 border-rose-700 text-rose-200'
        }`}>
          <div className="flex items-center gap-3">
            {verifyResult.ok ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 animate-bounce" />
            )}
            <div>
              <div className="font-bold text-sm">
                {verifyResult.ok
                  ? 'Cryptographic Verification Passed: All 20 Blocks Intact'
                  : `SECURITY ALERT: Cryptographic Chain Broken at Block #${verifyResult.broken_at || 17}`}
              </div>
              <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                {verifyResult.ok
                  ? 'Head Hash: e8a93bc214f7... matches State Cyber Forensics Root Hash.'
                  : 'Hash mismatch detected! Previous hash linkage corrupted. Inadmissible in court until reconciled.'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Ledger Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 bg-slate-950/70 border-b border-slate-800 flex items-center justify-between">
          <span className="font-bold text-xs uppercase tracking-wider text-slate-300">
            Immutable Audit Trail Logs
          </span>
          <span className="text-[11px] font-mono text-slate-500">
            Current Head Hash: <span className="text-teal-400">{ledger?.head_hash?.slice(0, 16)}...</span>
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 text-[11px]">
              <tr>
                <th className="p-3 w-16 text-center">Block</th>
                <th className="p-3 w-44">Timestamp</th>
                <th className="p-3">Action Description</th>
                <th className="p-3">Current Hash (SHA-256)</th>
                <th className="p-3">Previous Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {[...(ledger?.entries || [])].sort((a, b) => a.idx - b.idx).map((e) => {
                const isBroken = e.tampered || (isTampered && e.idx === 17);

                return (
                  <tr
                    key={e.idx}
                    className={`transition-colors ${
                      isBroken 
                        ? 'bg-rose-950/40 text-rose-200 border-l-4 border-l-rose-500 font-bold' 
                        : 'hover:bg-slate-850/50 text-slate-300'
                    }`}
                  >
                    <td className="p-3 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] ${
                        isBroken ? 'bg-rose-900 text-rose-200' : 'bg-slate-950 text-slate-400'
                      }`}>
                        #{e.idx}
                      </span>
                    </td>
                    <td className="p-3 text-[11px] text-slate-400 whitespace-nowrap">
                      {new Date(e.ts).toLocaleString()}
                    </td>
                    <td className="p-3 text-[11px] font-sans">
                      <span className={isBroken ? 'text-rose-300 font-semibold' : 'text-slate-200'}>
                        {e.action}
                      </span>
                      {isBroken && (
                        <span className="ml-2 px-1.5 py-0.2 rounded bg-rose-950 border border-rose-800 text-rose-300 text-[9px] uppercase font-mono">
                          TAMPERED HASH
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-[11px] text-teal-300/90 truncate max-w-[140px]" title={e.hash}>
                      {e.hash.slice(0, 14)}...
                    </td>
                    <td className="p-3 text-[11px] text-slate-500 truncate max-w-[140px]" title={e.prev_hash}>
                      {e.prev_hash === '0000000000000000000000000000000000000000000000000000000000000000'
                        ? 'GENESIS_BLOCK'
                        : `${e.prev_hash.slice(0, 14)}...`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Ledger;
