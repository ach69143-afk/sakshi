import React, { useState, useEffect } from 'react';
import { 
  GitMerge, 
  Check, 
  X, 
  ShieldAlert, 
  Sliders, 
  UserCheck, 
  Layers, 
  ArrowRight, 
  Phone, 
  Car, 
  FileText,
  AlertCircle,
  Sparkles
} from 'lucide-react';
import { getMergeQueueApi, approveMergeApi, rejectMergeApi, getSummaryApi } from '../api';
import { useAuth } from '../context/AuthContext';

export const MergeQueue = () => {
  const { user, hasRole } = useAuth();
  const [queue, setQueue] = useState([]);
  const [summary, setSummary] = useState(null);
  const [threshold, setThreshold] = useState(0.70);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState(null);
  const [collapsedId, setCollapsedId] = useState(null);

  const fetchQueue = async () => {
    try {
      const [data, sum] = await Promise.all([
        getMergeQueueApi(),
        getSummaryApi()
      ]);
      setQueue(data);
      setSummary(sum);
    } catch (err) {
      console.error("Merge queue load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [user?.role]);

  const canApprove = hasRole(['sp_dysp']);

  const handleApprove = async (id) => {
    if (!canApprove) return;
    try {
      setCollapsedId(id);
      await approveMergeApi(id);
      setActionMessage({ type: 'success', text: `Candidate ${id} approved by SP / DySP. Unified entity persona generated in knowledge graph.` });
      setTimeout(() => {
        fetchQueue();
        setCollapsedId(null);
      }, 1200);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.response?.data?.detail || 'Approval failed.' });
    }
  };

  const handleReject = async (id) => {
    if (!canApprove) return;
    try {
      await rejectMergeApi(id);
      setActionMessage({ type: 'info', text: `Candidate ${id} flagged as distinct profiles. Profiles kept separated.` });
      fetchQueue();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.response?.data?.detail || 'Rejection failed.' });
    }
  };

  const pendingCount = queue.filter(item => item.status === 'pending').length;
  const filteredQueue = queue.filter(item => item.score >= threshold);

  return (
    <div className="p-4 lg:p-6 space-y-6 max-w-6xl mx-auto w-full">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 lg:p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 text-xs font-mono font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30 rounded flex items-center gap-1.5">
              <GitMerge className="w-3.5 h-3.5 text-amber-400" />
              ENTITY RESOLUTION ENGINE
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Pending Candidates: {summary?.pending_merges ?? pendingCount}
            </span>
          </div>
          <h1 className="text-xl lg:text-2xl font-black text-slate-100 tracking-tight">
            Merge & Alias Reconciliation Queue
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Multi-factor probabilistic record linkage evaluating syntactic name similarity, shared vehicle registrations, co-located IMEIs, and banking accounts. Resolves fragmented alias nodes into unified investigative personas.
          </p>
        </div>

        {/* Threshold Slider */}
        <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex items-center gap-3">
          <Sliders className="w-4 h-4 text-teal-400" />
          <div className="text-xs">
            <div className="text-slate-400 font-mono text-[10px] uppercase">Linkage Threshold</div>
            <div className="flex items-center gap-2 mt-0.5">
              <input
                type="range"
                min="0.5"
                max="0.95"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-24 accent-teal-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
              />
              <span className="font-mono text-teal-300 font-bold w-10 text-right">
                {(threshold * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Action Notification Alert */}
      {actionMessage && (
        <div className={`p-4 rounded-xl border flex items-center justify-between text-xs animate-fade-in ${
          actionMessage.type === 'success' 
            ? 'bg-emerald-950/60 border-emerald-800 text-emerald-200' 
            : actionMessage.type === 'error'
            ? 'bg-rose-950/60 border-rose-800 text-rose-200'
            : 'bg-slate-900 border-slate-700 text-slate-300'
        }`}>
          <div className="flex items-center gap-2.5">
            <Sparkles className="w-4 h-4 text-teal-400" />
            <span>{actionMessage.text}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-slate-200">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Merge Queue Cards */}
      <div className="space-y-6">
        {filteredQueue.map((item) => {
          const isCollapsed = collapsedId === item.id;
          const isApproved = item.status === 'approved';
          const isRejected = item.status === 'rejected';

          return (
            <div
              key={item.id}
              className={`bg-slate-900 border rounded-2xl p-5 shadow-xl transition-all duration-700 ${
                isCollapsed
                  ? 'scale-95 opacity-50 bg-teal-950/30 border-teal-500'
                  : isApproved
                  ? 'border-emerald-800/80 bg-slate-900/60'
                  : isRejected
                  ? 'border-slate-800/80 opacity-60'
                  : 'border-slate-800 hover:border-slate-700'
              }`}
            >
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs px-2.5 py-1 rounded bg-slate-950 text-teal-300 font-bold border border-slate-800">
                    {item.id}
                  </span>
                  <div>
                    <h3 className="font-bold text-slate-100 text-sm">
                      Probabilistic Cross-Source Alias Cluster
                    </h3>
                    <div className="text-[11px] text-slate-400">
                      Comparing {item.records.length} distinct record profiles
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="text-[10px] uppercase font-mono text-slate-400">Resolution Confidence</div>
                    <div className="font-mono font-bold text-sm text-teal-300">
                      {Math.min(100, Math.max(0, Math.round((Number(item.score) || 0) <= 1 ? (Number(item.score) || 0) * 100 : (Number(item.score) || 0))))}% Match
                    </div>
                  </div>

                  <div className="relative group">
                    <div className="flex items-center gap-1.5">
                      {isApproved ? (
                        <span className="px-3 py-1.5 rounded-lg bg-emerald-950 border border-emerald-800 text-emerald-300 font-mono text-xs font-semibold">
                          ✓ Merged & Unified
                        </span>
                      ) : isRejected ? (
                        <span className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 font-mono text-xs">
                          Rejected
                        </span>
                      ) : (
                        <>
                          <button
                            onClick={() => handleApprove(item.id)}
                            disabled={!canApprove}
                            className={`px-3 py-1.5 rounded-lg font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 transition ${
                              canApprove
                                ? 'bg-teal-600 hover:bg-teal-500 text-slate-950 shadow-md shadow-teal-950'
                                : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed opacity-50'
                            }`}
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Approve Merge</span>
                          </button>
                          <button
                            onClick={() => handleReject(item.id)}
                            disabled={!canApprove}
                            className={`px-3 py-1.5 rounded-lg font-semibold text-xs border transition ${
                              canApprove
                                ? 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
                                : 'bg-slate-800 text-slate-500 border-slate-700 cursor-not-allowed opacity-50'
                            }`}
                          >
                            <X className="w-3.5 h-3.5" />
                            <span>Reject</span>
                          </button>
                        </>
                      )}
                    </div>
                    {!canApprove && !isApproved && !isRejected && (
                      <div className="absolute right-0 -top-8 px-2 py-1 bg-slate-800 border border-slate-700 text-[10px] text-slate-300 rounded shadow-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition pointer-events-none z-20">
                        Not permitted for {user?.role}. Merge approval reserved for SP / DySP only.
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Side-by-Side Record Cards */}
              <div className="py-4 grid grid-cols-1 md:grid-cols-3 gap-3">
                {item.records.map((rec) => (
                  <div
                    key={rec.record_id}
                    className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 text-xs space-y-2 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                        {rec.record_id}
                      </span>
                      <span className="text-[10px] text-teal-400 truncate max-w-[120px]">
                        {rec.source}
                      </span>
                    </div>

                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-mono">Profile Name</div>
                      <div className="font-bold text-slate-100 text-sm">{rec.name}</div>
                    </div>

                    <div className="space-y-1 pt-1 border-t border-slate-800/60 font-mono text-[11px]">
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <Phone className="w-3 h-3 text-slate-500" />
                        <span>{rec.phone}</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <Car className="w-3 h-3 text-slate-500" />
                        <span>{rec.plate}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Resolution Factors Score Breakdown Bars */}
              <div className="pt-3 border-t border-slate-800">
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Linkage Factor Contributions
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {item.reasons.map((r, idx) => (
                    <div key={idx} className="p-2 rounded-lg bg-slate-950/60 border border-slate-800/60 text-xs space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-slate-300">{r.factor}</span>
                        <span className="font-mono font-bold text-teal-300">{(r.value * 100).toFixed(0)}%</span>
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-teal-500 to-amber-500 h-full rounded-full"
                          style={{ width: `${r.value * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MergeQueue;
