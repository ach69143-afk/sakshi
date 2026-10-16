import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  AlertTriangle, 
  ShieldAlert, 
  Filter, 
  ExternalLink, 
  Clock, 
  ArrowRight, 
  Network,
  Search,
  Bug
} from 'lucide-react';
import { getAlertsApi, getSummaryApi, simulateInsiderApi } from '../api';
import { useAuth } from '../context/AuthContext';
import EvidenceModal from '../components/EvidenceModal';

export const Alerts = () => {
  const { debugMode } = useAuth();
  const [alerts, setAlerts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEvidence, setSelectedEvidence] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const [data, sum] = await Promise.all([
          getAlertsApi(),
          getSummaryApi()
        ]);
        setAlerts(data);
        setSummary(sum);
      } catch (err) {
        console.error("Alerts fetch error:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchAlerts();
  }, []);

  const severityOrder = { high: 1, med: 2, low: 3 };

  const sortedAlerts = [...alerts].sort((a, b) => {
    const sA = severityOrder[a.severity] || 99;
    const sB = severityOrder[b.severity] || 99;
    return sA - sB;
  });

  const filteredAlerts = sortedAlerts.filter(a => {
    if (filterSeverity !== 'all' && a.severity !== filterSeverity) return false;
    if (filterType !== 'all' && a.type !== filterType) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchTitle = a.title.toLowerCase().includes(q);
      const matchExpl = a.explanation.toLowerCase().includes(q);
      const matchEnt = a.entity_ids.some(e => e.toLowerCase().includes(q));
      if (!matchTitle && !matchExpl && !matchEnt) return false;
    }
    return true;
  });

  return (
    <div className="p-4 lg:p-6 space-y-6 max-w-6xl mx-auto w-full">
      {/* Evidence Drawer Modal */}
      <EvidenceModal evidenceId={selectedEvidence} onClose={() => setSelectedEvidence(null)} />

      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 lg:p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 text-xs font-mono font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30 rounded flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              INVESTIGATIVE TRIAGE
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Total Active Anomalies: {summary?.alerts_total ?? alerts.length}
            </span>
          </div>
          <h1 className="text-xl lg:text-2xl font-black text-slate-100 tracking-tight">
            Patterns Worthy of Investigator Attention
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Algorithmic flags highlighting structural bottlenecks, velocity thresholds, proximity clusters, and decoy nodes. Prioritized for tamper-evident forensic validation.
          </p>
        </div>

        {/* Quick Severity Counts */}
        {/* Quick Severity Counts & Debug Actions */}
        <div className="flex items-center gap-2">
          {debugMode && (
            <button
              onClick={async () => {
                setSimulating(true);
                try {
                  await simulateInsiderApi();
                  await fetchAlerts();
                } catch (err) {
                  console.error('Simulation error:', err);
                } finally {
                  setSimulating(false);
                }
              }}
              disabled={simulating}
              className="px-3 py-1.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-semibold flex items-center gap-1.5 transition shadow-lg shadow-amber-950/40 disabled:opacity-50"
              title="Append simulated adversary entries to ledger (DEBUG=1)"
            >
              <Bug className="w-3.5 h-3.5" />
              <span>{simulating ? 'Simulating...' : 'Simulate insider behaviour'}</span>
            </button>
          )}

          <div className="px-3 py-1.5 rounded-xl bg-slate-950 border border-rose-800/60 text-center">
            <div className="text-[10px] text-slate-400 font-mono uppercase">High</div>
            <div className="text-sm font-bold font-mono text-rose-400">
              {summary?.alerts_by_severity?.high ?? alerts.filter(a => a.severity === 'high' || a.severity === 'critical').length}
            </div>
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-slate-950 border border-amber-800/60 text-center">
            <div className="text-[10px] text-slate-400 font-mono uppercase">Med</div>
            <div className="text-sm font-bold font-mono text-amber-400">
              {summary?.alerts_by_severity?.medium ?? alerts.filter(a => a.severity === 'med' || a.severity === 'medium').length}
            </div>
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-700 text-center">
            <div className="text-[10px] text-slate-400 font-mono uppercase">Low</div>
            <div className="text-sm font-bold font-mono text-slate-300">
              {summary?.alerts_by_severity?.low ?? alerts.filter(a => a.severity === 'low').length}
            </div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search anomaly pattern, entity ID, or keyword..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500 transition"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Severity selector */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
            {['all', 'high', 'med', 'low'].map(s => (
              <button
                key={s}
                onClick={() => setFilterSeverity(s)}
                className={`px-2 py-0.5 rounded text-[11px] uppercase font-mono font-medium transition ${
                  filterSeverity === s ? 'bg-slate-800 text-teal-300 font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Type selector */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-teal-500"
          >
            <option value="all">All Anomaly Modalities</option>
            <option value="insider_threat">Insider Threat (rules + z-score)</option>
            <option value="prompt_injection">Prompt Injection Attempt</option>
            <option value="bridge_node">Bridge Node / Articulation</option>
            <option value="golden_hour">Golden Hour Proximity</option>
            <option value="pass_through">Pass-through Banking Relay</option>
            <option value="digital_bait">Digital Bait / Ad Lure</option>
            <option value="toll_anomaly">Toll NH-53 ANPR Anomaly</option>
            <option value="co_traveler">Cellular Co-traveler</option>
          </select>
        </div>
      </div>

      {/* Alert Cards List */}
      <div className="space-y-3.5">
        {filteredAlerts.map((a) => {
          const isHigh = a.severity === 'high';
          const isMed = a.severity === 'med';

          return (
            <div
              key={a.id}
              className={`p-4 lg:p-5 rounded-2xl border transition-all duration-300 bg-slate-900/90 shadow-xl ${
                isHigh 
                  ? 'border-rose-900/60 hover:border-rose-500/80 hover:bg-slate-900' 
                  : isMed
                  ? 'border-amber-900/60 hover:border-amber-500/80 hover:bg-slate-900'
                  : 'border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2.5">
                  <span className={`px-2 py-0.5 text-xs font-mono font-bold uppercase rounded ${
                    isHigh
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                      : isMed
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      : 'bg-slate-800 text-slate-300 border border-slate-700'
                  }`}>
                    {a.severity} SEVERITY
                  </span>
                  <span className="font-mono text-xs text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                    {a.id}
                  </span>
                  <span className="text-xs uppercase font-mono text-teal-400">
                    {a.type.replace('_', ' ')}
                  </span>
                </div>

                <span className="text-xs font-mono text-slate-500 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  {new Date(a.ts).toLocaleString()}
                </span>
              </div>

              <h2 className="text-sm font-bold text-slate-100 mb-1.5">
                {a.title}
              </h2>

              <p className="text-xs text-slate-300 leading-relaxed mb-3">
                {a.explanation}
              </p>

              <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
                {/* Entities linked */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-slate-500 text-[11px]">Associated Entities:</span>
                  {a.entity_ids.map(eid => (
                    <span
                      key={eid}
                      className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-950 text-slate-200 border border-slate-800"
                    >
                      {eid}
                    </span>
                  ))}
                </div>

                {/* Evidence citations & Action */}
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1 flex-wrap">
                    <span className="text-slate-500 text-[11px]">Citations:</span>
                    {a.evidence_ids.map(eid => (
                      <button
                        key={eid}
                        onClick={() => setSelectedEvidence(eid)}
                        className="font-mono text-[10px] text-teal-300 bg-slate-800 px-1.5 py-0.5 rounded hover:bg-slate-700 transition"
                      >
                        {eid}
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={() => navigate('/network')}
                    className="text-xs font-semibold text-teal-400 hover:text-teal-300 flex items-center gap-1 transition"
                  >
                    <span>View Graph</span>
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Alerts;
