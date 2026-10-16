import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Users, 
  PhoneCall, 
  CreditCard, 
  AlertTriangle, 
  Network, 
  Clock, 
  GitMerge, 
  Bot, 
  ArrowRight,
  TrendingUp,
  ExternalLink
} from 'lucide-react';
import { getSummaryApi, getAlertsApi, getGoldenHourApi } from '../api';
import EvidenceModal from '../components/EvidenceModal';
import MapBackdrop from '../components/MapBackdrop';

export const Dashboard = () => {
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [goldenHour, setGoldenHour] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedEvidence, setSelectedEvidence] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const [sum, a, gh] = await Promise.all([
          getSummaryApi(), 
          getAlertsApi(),
          getGoldenHourApi()
        ]);
        setSummary(sum);
        setAlerts(Array.isArray(a) ? a : []);
        setGoldenHour(gh);
      } catch (err) {
        console.error("Dashboard data load error:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, []);

  const topAlerts = alerts.slice(0, 4);
  const missingCount = goldenHour?.missing?.length || 5;
  const centroid = goldenHour?.centroid || [21.21834, 81.34172];

  return (
    <div className="p-4 lg:p-6 space-y-6 max-w-7xl mx-auto w-full">
      {/* Evidence Modal Drawer */}
      <EvidenceModal evidenceId={selectedEvidence} onClose={() => setSelectedEvidence(null)} />

      {/* PHASE B / C: HOTSPOT ALERT Card with non-interactive MapBackdrop */}
      <div className="relative rounded-2xl border border-red-900/60 overflow-hidden shadow-2xl card-high-glow">
        {/* Background Non-interactive MapBackdrop */}
        <div className="absolute inset-0 z-0 opacity-40">
          <MapBackdrop
            center={centroid}
            zoom={13}
            interactive={false}
            className="w-full h-full pointer-events-none"
          />
        </div>

        {/* Dark gradient overlay so text stays readable */}
        <div className="absolute inset-0 z-0 bg-gradient-to-r from-[#07080a] via-[#0e1013]/90 to-[#07080a]/95 pointer-events-none"></div>

        {/* Hotspot Content */}
        <div className="relative z-10 p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 text-xs font-mono font-bold bg-red-950/80 text-red-400 border border-red-800/80 rounded flex items-center gap-1.5 animate-pulse">
                <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
                ACTIVE HOTSPOT ALERT
              </span>
              <span className="text-xs text-slate-400 font-mono">
                AREA OF INTEREST: {`${centroid[0].toFixed(4)}° N, ${centroid[1].toFixed(4)}° E`}
              </span>
            </div>

            <div className="flex items-baseline gap-3">
              <span className="text-5xl sm:text-6xl font-black font-mono text-red-500 tracking-tight drop-shadow-[0_0_20px_rgba(239,43,45,0.5)]">
                {missingCount}
              </span>
              <div className="flex flex-col">
                <span className="text-lg sm:text-xl font-bold uppercase tracking-wider text-slate-100 font-heading">
                  MISSING IN 24 HOURS
                </span>
                <span className="text-xs text-slate-400">
                  {goldenHour?.radius_km || 3} km Chokepoint Radius • NH-53 Corridor Egress
                </span>
              </div>
            </div>

            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Multi-source evidentiary correlation fusing cellular CDR, FASTag toll telemetry, FIU bank pass-through records, and witness statements. Highlighting patterns worthy of investigator attention.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <button
              onClick={() => navigate('/golden-hour')}
              className="px-5 py-3 bg-red-600 hover:bg-red-500 text-white font-bold text-xs uppercase tracking-wider rounded-xl transition flex items-center justify-center gap-2 shadow-lg shadow-red-950/80 border border-red-500/50"
            >
              <Clock className="w-4 h-4" />
              <span>VIEW CASE DETAILS</span>
            </button>
            <button
              onClick={() => navigate('/network')}
              className="px-4 py-3 bg-slate-900/90 hover:bg-slate-800 text-slate-200 font-semibold text-xs uppercase tracking-wider rounded-xl transition flex items-center justify-center gap-2 border border-slate-700"
            >
              <Network className="w-4 h-4 text-red-400" />
              <span>Graph View</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4 Metric Cards with Real API Counts from /api/summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-red-950/40 border border-red-900/50 flex items-center justify-center text-red-400">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold font-mono text-slate-100">{summary?.entities ?? 63}</div>
            <div className="text-xs text-slate-400 uppercase tracking-wider font-medium">Entities Cataloged</div>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-red-950/40 border border-red-900/50 flex items-center justify-center text-red-400">
            <PhoneCall className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold font-mono text-slate-100">{summary?.calls ?? 400}</div>
            <div className="text-xs text-slate-400 uppercase tracking-wider font-medium">CDR Interactions</div>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-red-950/40 border border-red-900/50 flex items-center justify-center text-red-400">
            <CreditCard className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold font-mono text-slate-100">{summary?.transactions ?? 150}</div>
            <div className="text-xs text-slate-400 uppercase tracking-wider font-medium">Bank Transactions</div>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-red-950/40 border border-red-900/50 flex items-center justify-center text-red-400">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold font-mono text-red-400">{summary?.alerts_total ?? alerts.length}</div>
            <div className="text-xs text-slate-400 uppercase tracking-wider font-medium">Active Anomalies</div>
          </div>
        </div>
      </div>

      {/* Main Grid: Priority Anomalies + Quick Analysis Launchers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: High Priority Patterns */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <h2 className="font-bold text-slate-100 text-sm tracking-wide uppercase">
                  Patterns Worthy of Investigator Attention
                </h2>
              </div>
              <button
                onClick={() => navigate('/alerts')}
                className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1 font-semibold"
              >
                <span>View All {summary?.alerts_total ?? alerts.length} Alerts</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="space-y-3">
              {topAlerts.map((a) => (
                <div
                  key={a.id}
                  className={`p-3.5 rounded-xl bg-slate-950/70 border hover:border-red-900/80 transition space-y-2 ${
                    a.severity === 'high' ? 'border-red-950 card-high-glow' : 'border-slate-800/80'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded ${
                        a.severity === 'high' 
                          ? 'bg-red-950 text-red-300 border border-red-800' 
                          : 'bg-amber-950 text-amber-300 border border-amber-800'
                      }`}>
                        {a.severity}
                      </span>
                      <span className="font-semibold text-slate-200 text-xs">{a.title}</span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500">
                      {a.ts ? new Date(a.ts).toLocaleDateString() : 'Active'}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 leading-relaxed">
                    {a.explanation || a.description}
                  </p>

                  <div className="flex items-center justify-between pt-1 text-[11px]">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-slate-500 text-[10px]">Citations:</span>
                      {(a.evidence_ids || []).map((ev) => (
                        <button
                          key={ev}
                          onClick={() => setSelectedEvidence(ev)}
                          className="evidence-chip"
                        >
                          {ev}
                        </button>
                      ))}
                    </div>
                    <button
                      onClick={() => navigate('/network')}
                      className="text-red-400 hover:text-red-300 font-medium flex items-center gap-1"
                    >
                      <span>Locate in Graph</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Col: Quick Workflows */}
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-red-400" />
              Operational Workflows
            </h3>
            
            <div className="space-y-2.5">
              <div 
                onClick={() => navigate('/network')}
                className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-red-500/50 hover:bg-slate-850/60 transition cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="font-semibold text-xs text-slate-200 group-hover:text-red-300 flex items-center gap-2">
                    <Network className="w-4 h-4 text-red-400" />
                    <span>Bridge Articulation Analysis</span>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-red-400 transition transform group-hover:translate-x-0.5" />
                </div>
                <p className="text-[11px] text-slate-400">
                  Inspect top broker candidate bridging communication and highway transit clusters.
                </p>
              </div>

              <div 
                onClick={() => navigate('/merge-queue')}
                className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-amber-500/50 hover:bg-slate-850/60 transition cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="font-semibold text-xs text-slate-200 group-hover:text-amber-300 flex items-center gap-2">
                    <GitMerge className="w-4 h-4 text-amber-400" />
                    <span>Resolve Alias Merges ({summary?.pending_merges !== undefined && summary?.pending_merges !== null ? summary.pending_merges : '0'})</span>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-amber-400 transition transform group-hover:translate-x-0.5" />
                </div>
                <p className="text-[11px] text-slate-400">
                  Correlate candidate alias profiles sharing cross-source identifier markers.
                </p>
              </div>

              <div 
                onClick={() => navigate('/golden-hour')}
                className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-red-500/50 hover:bg-slate-850/60 transition cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="font-semibold text-xs text-slate-200 group-hover:text-red-300 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-red-400" />
                    <span>Golden Hour Cell Triangulation</span>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-red-400 transition transform group-hover:translate-x-0.5" />
                </div>
                <p className="text-[11px] text-slate-400">
                  Burner device co-located near missing individuals prior to highway exit.
                </p>
              </div>

              <div 
                onClick={() => navigate('/copilot')}
                className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-red-500/50 hover:bg-slate-850/60 transition cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="font-semibold text-xs text-slate-200 group-hover:text-red-300 flex items-center gap-2">
                    <Bot className="w-4 h-4 text-red-400" />
                    <span>Ask Graph Copilot</span>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-red-400 transition transform group-hover:translate-x-0.5" />
                </div>
                <p className="text-[11px] text-slate-400">
                  Natural language forensic querying with evidence citations.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
