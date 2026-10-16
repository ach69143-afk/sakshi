import React, { useState, useEffect } from 'react';
import { 
  GitMerge, 
  ShieldCheck, 
  ShieldAlert, 
  AlertCircle, 
  Check, 
  X, 
  Lock, 
  ExternalLink, 
  Tag, 
  FileText, 
  RefreshCw,
  EyeOff,
  Filter,
  CheckCircle2,
  XCircle,
  HelpCircle
} from 'lucide-react';
import { getCrossCaseLinksApi, decideCrossCaseLinkApi } from '../api';
import { useAuth } from '../context/AuthContext';

export const CrossCase = () => {
  const { user } = useAuth();
  const [links, setLinks] = useState([]);
  const [suppressed, setSuppressed] = useState([]);
  const [loading, setLoading] = useState(true);
  const [decidingId, setDecidingId] = useState(null);
  const [toast, setToast] = useState(null);

  const isReviewerRole = user && ['ig', 'sp_dysp', 'sp_dysp_raipur'].includes(user.role);

  const fetchLinks = async () => {
    setLoading(true);
    try {
      const data = await getCrossCaseLinksApi();
      setLinks(Array.isArray(data?.links) ? data.links : []);
      setSuppressed(Array.isArray(data?.suppressed) ? data.suppressed : []);
    } catch (err) {
      console.error('Failed to load cross-case links:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLinks();
  }, [user?.role]);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  const handleDecision = async (linkId, decision) => {
    setDecidingId(linkId);
    try {
      const res = await decideCrossCaseLinkApi(linkId, decision);
      showToast(
        `Link ${decision === 'approve' ? 'Approved' : 'Rejected'} successfully. Action committed to ledger.`,
        'success'
      );
      fetchLinks();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Authorization failed for decision';
      showToast(detail, 'error');
    } finally {
      setDecidingId(null);
    }
  };

  const pendingLinks = links.filter(l => !l.blind && l.status === 'pending');
  const blindLinks = links.filter(l => l.blind);
  const decidedLinks = links.filter(l => !l.blind && l.status !== 'pending');

  return (
    <div className="p-4 lg:p-6 space-y-6 max-w-7xl mx-auto w-full">
      {/* Toast Notification */}
      {toast && (
        <div className={`fixed top-16 right-6 z-50 max-w-md px-4 py-3 rounded-xl shadow-2xl border flex items-start gap-3 transition-all ${
          toast.type === 'success' 
            ? 'bg-emerald-950/95 border-emerald-700 text-emerald-200' 
            : 'bg-rose-950/95 border-rose-700 text-rose-200'
        }`}>
          {toast.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1 text-xs">
            <div className="font-bold mb-0.5">{toast.type === 'success' ? 'Cross-Case Decision' : 'Authorization Denied'}</div>
            <div className="font-mono text-[11px] leading-relaxed">{toast.message}</div>
          </div>
          <button onClick={() => setToast(null)} className="p-0.5 rounded hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-red-950/60 text-red-400 border border-red-800/60 shadow-lg shadow-red-950/40">
              <GitMerge className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Cross-Case Intelligence Links
                <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-red-900/40 text-red-300 border border-red-800/80">
                  {links.length} Discovered
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Automated multi-jurisdictional identifier correlation powered by privacy-preserving HMAC matching and noisy-OR scoring.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={fetchLinks}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700 transition self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-red-400' : ''}`} />
          <span>Refresh Links</span>
        </button>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-44 rounded-xl bg-slate-900/60 border border-slate-800 animate-pulse"></div>
          ))}
        </div>
      ) : (
        <div className="space-y-8">
          {/* Section 1: Active / Pending Cross-Case Links */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <span>Active Link Suggestions</span>
                <span className="px-2 py-0.5 rounded-full text-xs font-mono bg-red-950 text-red-300 border border-red-800/80">
                  {pendingLinks.length} Pending
                </span>
              </h2>
            </div>

            {pendingLinks.length === 0 && blindLinks.length === 0 && (
              <div className="p-8 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400 text-xs">
                No pending cross-case correlation links found for your current jurisdiction access.
              </div>
            )}

            <div className="grid grid-cols-1 gap-4">
              {pendingLinks.map((link) => (
                <div
                  key={link.id}
                  className="rounded-2xl bg-slate-900/70 border border-slate-800 hover:border-red-900/60 transition p-5 flex flex-col md:flex-row md:items-center justify-between gap-5 shadow-lg"
                >
                  <div className="space-y-3 flex-1">
                    {/* Top Badges */}
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-red-950 text-red-300 border border-red-800/80">
                        {link.identifier_type || 'Shared ID'}
                      </span>

                      <div className="flex items-center gap-1.5 font-mono text-xs px-2.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300 font-semibold">
                        <span className="text-red-400">{link.case_a}</span>
                        <span className="text-slate-500">⇄</span>
                        <span className="text-blue-400">{link.case_b}</span>
                      </div>

                      <div className="flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 font-mono font-semibold">
                        <span>Score:</span>
                        <span className="font-bold">{link.score}</span>
                      </div>

                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-400 border border-amber-500/30">
                        Pending Decision
                      </span>
                    </div>

                    {/* Masked / Display Identifier */}
                    <div className="flex items-baseline gap-3">
                      <span className="text-xs text-slate-400 font-medium">Shared Value:</span>
                      <span className="font-mono text-base font-bold text-white tracking-wider bg-slate-950 px-3 py-1 rounded-md border border-slate-800">
                        {link.identifier_display || link.identifier_masked || 'XXXXX'}
                      </span>
                      {link.identifier_display === link.identifier_masked && (
                        <span className="text-[10px] text-slate-500 flex items-center gap-1">
                          <EyeOff className="w-3 h-3" />
                          Role-masked
                        </span>
                      )}
                    </div>

                    {/* Reasons / Explanation */}
                    {link.reasons && link.reasons.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Analysis:</div>
                        <ul className="text-xs text-slate-300 space-y-0.5 list-disc list-inside">
                          {link.reasons.map((r, idx) => (
                            <li key={idx} className="leading-relaxed">{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Evidence Chips */}
                    {link.evidence && link.evidence.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="text-[11px] text-slate-400 font-medium mr-1">Corroborating Evidence:</span>
                        {link.evidence.map((ev, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1 text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-950 text-teal-300 border border-slate-800 shadow-sm"
                          >
                            <Tag className="w-3 h-3 text-teal-400" />
                            {ev}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Approve / Reject Controls */}
                  <div className="flex flex-row md:flex-col gap-2 flex-shrink-0 justify-end pt-3 md:pt-0 border-t md:border-t-0 border-slate-800">
                    <button
                      onClick={() => handleDecision(link.id, 'approve')}
                      disabled={decidingId === link.id}
                      className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/40 transition disabled:opacity-50"
                    >
                      <Check className="w-4 h-4" />
                      <span>Approve Link</span>
                    </button>

                    <button
                      onClick={() => handleDecision(link.id, 'reject')}
                      disabled={decidingId === link.id}
                      className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-slate-800 hover:bg-rose-950 hover:text-rose-300 text-slate-300 border border-slate-700 transition disabled:opacity-50"
                    >
                      <X className="w-4 h-4" />
                      <span>Reject</span>
                    </button>
                  </div>
                </div>
              ))}

              {/* Blind Matches Rendering */}
              {blindLinks.map((blind, idx) => (
                <div
                  key={blind.id || idx}
                  className="relative rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 overflow-hidden shadow-lg backdrop-blur-sm"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-amber-400 shadow-inner">
                        <Lock className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-slate-200">
                          Possible link to a case outside your access
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5">
                          Cryptographic hash match detected with an external operational file. Blinded under zero-knowledge privacy policy.
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-start sm:self-auto">
                      <button
                        disabled
                        className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800/80 text-slate-500 border border-slate-700/60 cursor-not-allowed flex items-center gap-1.5"
                      >
                        <Lock className="w-3 h-3" />
                        <span>Request Access</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-900 text-amber-400 border border-slate-800">
                          Coming soon
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section 2: Decided Links History (if any) */}
          {decidedLinks.length > 0 && (
            <div className="space-y-4 pt-4 border-t border-slate-800">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <span>Decided Cross-Case Links ({decidedLinks.length})</span>
              </h2>
              <div className="grid grid-cols-1 gap-3">
                {decidedLinks.map(link => (
                  <div key={link.id} className="p-4 rounded-xl bg-slate-900/30 border border-slate-800 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800">
                        {link.case_a} ⇄ {link.case_b}
                      </span>
                      <span className="font-mono font-bold text-white">{link.identifier_display || link.identifier_masked}</span>
                      <span className="text-slate-400">Score: {link.score}</span>
                    </div>
                    <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase text-[10px] ${
                      link.status === 'approved' 
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' 
                        : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                    }`}>
                      {link.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section 3: Suppressed (Common Identifiers) Section */}
          <div className="space-y-4 pt-4 border-t border-slate-800">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                  <Filter className="w-4 h-4 text-slate-400" />
                  <span>Suppressed (Common Identifiers)</span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-mono bg-slate-800 text-slate-400 border border-slate-700">
                    {suppressed.length} Suppressed
                  </span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Public infrastructure and high-frequency decoy numbers automatically suppressed to avoid false correlation.
                </p>
              </div>
            </div>

            {suppressed.length === 0 ? (
              <div className="p-6 text-center rounded-xl bg-slate-900/30 border border-slate-800 text-slate-400 text-xs">
                No identifiers currently suppressed.
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3">
                {suppressed.map((sup, idx) => (
                  <div
                    key={sup.id || idx}
                    className="p-4 rounded-xl bg-slate-900/30 border border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800 font-semibold">
                        {sup.case_a} ⇄ {sup.case_b}
                      </span>
                      <span className="font-mono text-slate-300 font-medium">
                        {sup.identifier || sup.identifier_masked || 'Common Phone / Service'}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-800/50">
                        Reason: {sup.reason || 'common identifier'}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 self-start sm:self-auto">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-800 text-slate-400 border border-slate-700">
                        Suppressed
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CrossCase;
