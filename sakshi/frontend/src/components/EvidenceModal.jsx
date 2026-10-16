import React from 'react';
import { X, ShieldCheck, FileText, Hash, Calendar, Layers } from 'lucide-react';

export const EvidenceModal = ({ evidenceId, onClose }) => {
  if (!evidenceId) return null;

  const item = {
    id: evidenceId,
    title: `Investigative Forensic Record ${evidenceId}`,
    type: evidenceId.startsWith('CDR') 
      ? 'Telecommunication Records (CDR)'
      : evidenceId.startsWith('TXN')
      ? 'Financial Intelligence (FIU/Bank Log)'
      : evidenceId.startsWith('TOLL')
      ? 'National Highway ANPR & Toll Telemetry'
      : evidenceId.startsWith('GEO')
      ? 'Geospatial Tower Dump & Sector Analysis'
      : 'Chain of Custody Investigative Record',
    ts: '2026-09-26 12:00:00 IST',
    hash: '7a8b9c0d1e2f3a4b5c6d7e8f90a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9',
    source: 'Verified Evidence Vault / Law Enforcement Telemetry Nodal Unit',
    text: `Verified evidentiary artifact ${evidenceId} cataloged under active case registry. Corroborates pattern worthy of investigator attention across correlated telecommunication and transit vectors.`
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-[#0e1013] border border-[#2b1416] rounded-xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#2b1416] flex items-center justify-between bg-[#07080a]">
          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 text-xs font-mono font-bold bg-red-950/60 text-red-300 border border-red-800/60 rounded">
              {item.id}
            </span>
            <div>
              <h3 className="font-semibold text-slate-100 text-sm">{item.title}</h3>
              <p className="text-xs text-slate-400">{item.type}</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-[#14171b] transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 overflow-y-auto">
          {/* Metadata badges */}
          <div className="grid grid-cols-2 gap-3 p-3 bg-[#14171b] rounded-lg border border-[#2b1416] text-xs">
            <div className="flex items-center gap-2 text-slate-400">
              <Calendar className="w-4 h-4 text-amber-400" />
              <span>Timestamp: <span className="font-mono text-slate-200">{item.ts}</span></span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <Layers className="w-4 h-4 text-red-400" />
              <span>Source: <span className="text-slate-200 truncate">{item.source}</span></span>
            </div>
          </div>

          {/* Transcript / Excerpt */}
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-slate-400 mb-1.5 block flex items-center gap-1.5 font-condensed">
              <FileText className="w-3.5 h-3.5 text-red-400" />
              Official Case Transcript / Data Extract
            </label>
            <div className="p-4 bg-[#07080a] rounded-lg border border-[#2b1416] font-mono text-xs leading-relaxed text-slate-300">
              {item.text}
            </div>
          </div>

          {/* Cryptographic Hash */}
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-slate-400 mb-1 block flex items-center gap-1.5 font-condensed">
              <Hash className="w-3.5 h-3.5 text-amber-400" />
              Cryptographic SHA-256 Digest
            </label>
            <div className="p-2.5 bg-[#07080a] rounded-lg border border-[#2b1416] font-mono text-[11px] text-red-300/90 break-all select-all">
              {item.hash}
            </div>
          </div>

          {/* Defensibility Notice */}
          <div className="p-3 bg-red-950/20 border border-red-900/40 rounded-lg flex items-center gap-2.5 text-xs text-red-200">
            <ShieldCheck className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>Cryptographically anchored in SAKSHI Audit Chain. EVIDENCE-LINKED and tamper-evident under supervisory audit protocol.</span>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#2b1416] bg-[#07080a] flex items-center justify-between text-xs text-slate-400">
          <span>Synthetic sample dataset for investigative training</span>
          <button 
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-[#14171b] hover:bg-[#1f242b] border border-[#2b1416] text-slate-200 font-medium transition"
          >
            Close Drawer
          </button>
        </div>
      </div>
    </div>
  );
};

export default EvidenceModal;
