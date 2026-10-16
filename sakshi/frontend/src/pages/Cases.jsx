import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FolderKanban, 
  MapPin, 
  Users, 
  PhoneCall, 
  CreditCard, 
  AlertTriangle, 
  GitMerge, 
  ArrowRight, 
  CheckCircle2, 
  ShieldCheck,
  RefreshCw
} from 'lucide-react';
import { getCasesApi, getActiveCaseId, setActiveCaseId } from '../api';

export const Cases = () => {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState(getActiveCaseId());
  const navigate = useNavigate();

  const loadCases = async () => {
    setLoading(true);
    try {
      const data = await getCasesApi();
      setCases(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load cases:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
    const handleCaseChanged = (e) => {
      setActiveId(e.detail?.caseId || getActiveCaseId());
    };
    window.addEventListener('sakshi-case-changed', handleCaseChanged);
    return () => window.removeEventListener('sakshi-case-changed', handleCaseChanged);
  }, []);

  const handleOpenCase = (caseId) => {
    setActiveCaseId(caseId);
    setActiveId(caseId);
    navigate('/dashboard');
  };

  return (
    <div className="p-4 lg:p-6 space-y-6 max-w-7xl mx-auto w-full">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-red-950/60 text-red-400 border border-red-800/60 shadow-lg shadow-red-950/40">
              <FolderKanban className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Operational Case Registry
                <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-red-900/40 text-red-300 border border-red-800/80">
                  {cases.length} Authorized {cases.length === 1 ? 'Case' : 'Cases'}
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Multi-jurisdiction case files assigned to your credentials. Select a case to switch operational context.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={loadCases}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700 transition self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-red-400' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Case Cards Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map((i) => (
            <div key={i} className="h-64 rounded-xl bg-slate-900/60 border border-slate-800 animate-pulse p-6"></div>
          ))}
        </div>
      ) : cases.length === 0 ? (
        <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400">
          No authorized cases assigned to your account.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {cases.map((c) => {
            const isCurrent = c.case_id === activeId;
            return (
              <div
                key={c.case_id}
                onClick={() => handleOpenCase(c.case_id)}
                className={`group relative rounded-2xl border transition-all duration-200 cursor-pointer p-6 flex flex-col justify-between ${
                  isCurrent
                    ? 'bg-slate-900/90 border-red-600/80 shadow-xl shadow-red-950/30 ring-1 ring-red-500/50'
                    : 'bg-slate-900/40 hover:bg-slate-900/70 border-slate-800 hover:border-slate-700'
                }`}
              >
                {/* Header Row */}
                <div>
                  <div className="flex items-center justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm px-2.5 py-1 rounded-md font-bold bg-slate-950 text-red-400 border border-red-900/60 shadow-inner">
                        {c.case_id}
                      </span>
                      <span className="flex items-center gap-1 text-xs text-slate-400 font-medium">
                        <MapPin className="w-3.5 h-3.5 text-slate-500" />
                        {c.district} District
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {isCurrent && (
                        <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          <CheckCircle2 className="w-3 h-3" />
                          Active Context
                        </span>
                      )}
                      <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                        {c.status || 'Open'}
                      </span>
                    </div>
                  </div>

                  <h3 className="text-lg font-bold text-white group-hover:text-red-300 transition mb-4">
                    {c.title}
                  </h3>

                  {/* 4 Stat Counters */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1">
                        <Users className="w-3.5 h-3.5 text-blue-400" />
                        <span>Entities</span>
                      </div>
                      <div className="text-lg font-mono font-bold text-white">{c.entities ?? 0}</div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1">
                        <PhoneCall className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Calls</span>
                      </div>
                      <div className="text-lg font-mono font-bold text-white">{c.calls ?? 0}</div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1">
                        <CreditCard className="w-3.5 h-3.5 text-purple-400" />
                        <span>Transactions</span>
                      </div>
                      <div className="text-lg font-mono font-bold text-white">{c.transactions ?? 0}</div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                        <span>Alerts</span>
                      </div>
                      <div className="text-lg font-mono font-bold text-amber-300">{c.alerts ?? 0}</div>
                    </div>
                  </div>
                </div>

                {/* Footer Action Row */}
                <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs">
                    <GitMerge className="w-4 h-4 text-red-400" />
                    <span className="text-slate-400">Cross-case links:</span>
                    <span className="font-mono font-bold px-1.5 py-0.5 rounded bg-red-950/80 text-red-300 border border-red-800/60 text-[11px]">
                      {c.pending_links ?? 0} pending
                    </span>
                  </div>

                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-red-400 group-hover:text-red-300 transition">
                    <span>{isCurrent ? 'Switch View' : 'Open Case'}</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Cases;
