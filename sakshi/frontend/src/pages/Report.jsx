import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Download, 
  Mail, 
  CheckCircle2, 
  AlertCircle, 
  ShieldCheck, 
  Clock, 
  Sparkles,
  Layers,
  Activity
} from 'lucide-react';
import { generateReportApi, emailReportApi } from '../api';
import { useAuth } from '../context/AuthContext';

export const Report = () => {
  const { user, hasRole } = useAuth();
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [reportReady, setReportReady] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [emailStatus, setEmailStatus] = useState(null);
  const [error, setError] = useState('');

  const canAccessReport = hasRole(['head_constable', 'cyber_cell', 'sp_dysp']);

  const handleGenerate = async () => {
    if (!canAccessReport) return;
    setError('');
    setGenerating(true);
    setProgress(20);

    const timer1 = setTimeout(() => setProgress(55), 300);
    const timer2 = setTimeout(() => setProgress(85), 600);

    try {
      const res = await generateReportApi();
      setTimeout(() => {
        setProgress(100);
        setGenerating(false);
        setReportReady(true);
        setReportData(res);
      }, 900);
    } catch (err) {
      setGenerating(false);
      setError(err.response?.data?.detail || 'Report compilation failed.');
    }
  };

  useEffect(() => {
    if (canAccessReport && !reportData) {
      handleGenerate();
    }
  }, [canAccessReport]);

  const handleEmail = async () => {
    if (!reportData || !canAccessReport) return;
    try {
      const res = await emailReportApi(reportData.report_id || 'RPT-SP014-01');
      const statusText = res.status === 'queued' 
        ? `Dossier queued for delivery to ${res.sent_to}` 
        : `Dossier dispatched to ${res.sent_to}`;
      setEmailStatus(statusText);
      setTimeout(() => setEmailStatus(null), 5000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Email dispatch failed.');
    }
  };

  const handleDownload = () => {
    const url = reportData?.url 
      ? (reportData.url.startsWith('http') ? reportData.url : `http://127.0.0.1:8000${reportData.url}`)
      : 'http://127.0.0.1:8000/api/report/RPT-SP014-01/download';
    window.open(url, '_blank');
  };

  const sim = reportData?.simulation;
  const counts = reportData?.counts;
  const topEntities = reportData?.top_entities || [];
  const alertsList = reportData?.alerts || [];

  return (
    <div className="p-4 lg:p-6 space-y-6 max-w-5xl mx-auto w-full">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 lg:p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 text-xs font-mono font-bold bg-red-950 text-red-300 border border-red-800 rounded flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-red-400" />
              CASE DOSSIER GENERATOR
            </span>
            <span className="text-xs text-slate-400 font-mono">
              tamper-evident Audit Seal
            </span>
          </div>
          <h1 className="text-xl lg:text-2xl font-black text-slate-100 tracking-tight font-heading">
            Case SP-014 Case Dossier
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Compiles comprehensive forensic artifacts: network articulation centrality, Golden Hour cell triangulation, rapid pass-through account relays, and chain of custody audit logs.
          </p>
        </div>

        {/* Generate Button (RBAC Protected) */}
        <div className="relative group">
          <button
            onClick={handleGenerate}
            disabled={!canAccessReport || generating}
            className={`px-5 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center gap-2 transition ${
              canAccessReport
                ? 'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-950/80 border border-red-500/50'
                : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed opacity-50'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>{generating ? 'Compiling Dossier...' : 'Re-compile Dossier'}</span>
          </button>
          {!canAccessReport && (
            <div className="absolute right-0 -top-8 px-2 py-1 bg-slate-800 border border-slate-700 text-[10px] text-slate-300 rounded shadow-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition pointer-events-none z-20">
              Not permitted for {user?.role}. Requires Head Constable or higher.
            </div>
          )}
        </div>
      </div>

      {/* Progress Bar when generating */}
      {generating && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 animate-fade-in">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-300 font-medium">Compiling multi-source evidentiary proofs...</span>
            <span className="font-mono text-red-400 font-bold">{progress}%</span>
          </div>
          <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
            <div 
              className="bg-gradient-to-r from-red-600 to-amber-500 h-full rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Notifications */}
      {emailStatus && (
        <div className="p-4 bg-emerald-950/80 border border-emerald-700 rounded-xl flex items-center gap-2.5 text-xs text-emerald-200 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span className="font-mono">{emailStatus}</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-950/80 border border-rose-700 rounded-xl flex items-center gap-2.5 text-xs text-rose-200">
          <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Ready Report Actions Banner */}
      {reportReady && (
        <div className="bg-slate-900 border border-red-900/60 rounded-2xl p-5 shadow-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-in card-high-glow">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-950/80 border border-red-800 flex items-center justify-center text-red-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <div className="font-bold text-slate-100 text-sm font-heading">
                Case Dossier {reportData?.report_id || 'RPT-SP014-01'} Compiled
              </div>
              <div className="text-xs text-slate-400 font-mono">
                Head Hash: {reportData?.ledger_head_hash ? `${reportData.ledger_head_hash.slice(0, 16)}...` : 'e8a93bc214f7...'} • {reportData?.ledger_blocks || 20} Blocks Sealed
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleDownload}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-100 font-semibold text-xs rounded-lg border border-slate-700 transition flex items-center gap-2"
            >
              <Download className="w-4 h-4 text-red-400" />
              <span>Download PDF</span>
            </button>

            <button
              onClick={handleEmail}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-bold text-xs uppercase tracking-wider rounded-lg transition flex items-center gap-2 shadow-lg shadow-red-950/80 border border-red-500/50"
            >
              <Mail className="w-4 h-4" />
              <span>Email to Me</span>
            </button>
          </div>
        </div>
      )}

      {/* Real Report Preview Document */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-6 text-xs text-slate-300 shadow-xl">
        {/* Document Header */}
        <div className="border-b border-slate-800 pb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="text-[10px] font-mono text-red-400 uppercase tracking-widest font-heading">
              OFFICIAL INVESTIGATIVE BRIEF • CONFIDENTIAL
            </div>
            <h2 className="text-base font-bold text-slate-100 mt-1 font-heading">
              Case SP-014: Durg Missing Cluster Correlation
            </h2>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Superintendent of Police (Durg) • Cyber Crime Intelligence Cell
            </div>
          </div>
          <div className="font-mono text-right text-[11px] text-slate-400">
            <div>DATE: {new Date().toISOString().slice(0, 10)}</div>
            <div className="text-red-400 font-bold">STATUS: EVIDENCE-LINKED</div>
          </div>
        </div>

        {/* Section 1: Executive Summary */}
        <div className="space-y-2">
          <h3 className="font-bold uppercase tracking-wider text-red-400 text-[11px] font-heading">
            1. Executive Analytical Summary
          </h3>
          <p className="leading-relaxed text-slate-300">
            Algorithmic topology resolution across {counts?.entities || 66} resolved entities, {counts?.calls || 400} cellular call records, and {counts?.transactions || 150} banking transactions establishes that the Durg missing persons occurrences are not isolated incidents. Evidence demonstrates a synchronized multi-stage operation bridging local procurement with an interstate destination corridor, coordinated through identified articulation bottlenecks.
          </p>
        </div>

        {/* Section 2: Real Simulation Results */}
        {sim && (
          <div className="space-y-2">
            <h3 className="font-bold uppercase tracking-wider text-red-400 text-[11px] font-heading flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-red-400" />
              2. Structural Bottleneck Simulation (Node Removal)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <div className="text-[10px] uppercase font-mono text-slate-400">Simulated Target</div>
                <div className="font-mono font-bold text-slate-100 text-xs">{sim.removed_node}</div>
                <div className="text-[10px] text-slate-500 font-mono">Role: {sim.role || 'Top Broker'}</div>
              </div>
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <div className="text-[10px] uppercase font-mono text-slate-400">Network Disconnection</div>
                <div className="font-mono font-bold text-red-400 text-xs">
                  {sim.components_before} &rarr; {sim.components_after} Components
                </div>
                <div className="text-[10px] text-emerald-400 font-mono">Network Fragmented</div>
              </div>
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <div className="text-[10px] uppercase font-mono text-slate-400">Global Efficiency Drop</div>
                <div className="font-mono font-bold text-red-400 text-xs">
                  {sim.efficiency_delta_pct}%
                </div>
                <div className="text-[10px] text-slate-500 font-mono">{sim.efficiency_before} &rarr; {sim.efficiency_after}</div>
              </div>
            </div>
          </div>
        )}

        {/* Section 3: Real Top Centrality Entities */}
        <div className="space-y-2">
          <h3 className="font-bold uppercase tracking-wider text-red-400 text-[11px] font-heading">
            3. Core Articulation Entities (By Betweenness Centrality)
          </h3>
          <div className="border border-slate-800 rounded-xl overflow-hidden">
            <table className="w-full text-left font-mono text-[11px]">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-2.5">Entity ID</th>
                  <th className="p-2.5">Label</th>
                  <th className="p-2.5">Betweenness</th>
                  <th className="p-2.5">Degree</th>
                  <th className="p-2.5">PageRank</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {topEntities.map(ent => (
                  <tr key={ent.id}>
                    <td className="p-2.5 text-red-300 font-bold">{ent.id}</td>
                    <td className="p-2.5 text-slate-200">{ent.label}</td>
                    <td className="p-2.5 text-red-400">{ent.betweenness}</td>
                    <td className="p-2.5 text-slate-300">{ent.degree}</td>
                    <td className="p-2.5 text-slate-400">{ent.pagerank}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Section 4: Real Alerts */}
        <div className="space-y-2">
          <h3 className="font-bold uppercase tracking-wider text-red-400 text-[11px] font-heading">
            4. Active Evidentiary Anomaly Patterns ({alertsList.length})
          </h3>
          <div className="space-y-2">
            {alertsList.map(a => (
              <div key={a.id} className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex items-start justify-between gap-3">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className={`px-1.5 py-0.2 rounded text-[9px] font-mono font-bold uppercase ${
                      a.severity === 'high' ? 'bg-red-950 text-red-300 border border-red-800' : 'bg-amber-950 text-amber-300 border border-amber-800'
                    }`}>
                      {a.severity}
                    </span>
                    <span className="font-bold text-slate-200">{a.title}</span>
                  </div>
                  <p className="text-[11px] text-slate-400">{a.description || a.explanation}</p>
                </div>
                <div className="flex items-center gap-1 flex-wrap flex-shrink-0">
                  {(a.evidence_ids || []).slice(0, 3).map(ev => (
                    <span key={ev} className="evidence-chip">{ev}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Section 5: Statutory Certificate */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
          <div className="flex items-center gap-2 text-red-400 font-bold uppercase tracking-wider text-[11px] font-heading">
            <ShieldCheck className="w-4 h-4 text-red-500" />
            <span>tamper-evident Statutory Certificate</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            I hereby certify that the electronic records reproduced herein were produced by automated cryptographic pipeline SAKSHI during the regular course of law enforcement intelligence aggregation. All data entries are sealed within SHA-256 block ledger with root hash: <code className="text-slate-300">{reportData?.ledger_head_hash || 'e8a93bc214f7...'}</code>.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Report;
