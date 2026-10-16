import React, { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Send, 
  Sparkles, 
  ShieldCheck, 
  FileText, 
  ExternalLink, 
  HelpCircle,
  Clock,
  RotateCcw
} from 'lucide-react';
import { askCopilotApi } from '../api';
import EvidenceModal from '../components/EvidenceModal';

const SUGGESTED_QUESTIONS = [
  "Who links the two groups?",
  "Summarize the missing-person cluster",
  "Which accounts show rapid pass-through?",
  "Show flights to Dubai"
];

export const AskCopilot = () => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: "Investigative Copilot online. I analyze structured evidence citations, graph centrality, and telemetry logs for Case SP-014 (Durg Missing Cluster). All answers are grounded strictly in evidentiary artifacts.",
      citations: [],
      confidence: null
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (queryText) => {
    const q = (queryText || inputQuery).trim();
    if (!q || loading) return;

    const userMessage = { role: 'user', text: q };
    setMessages(prev => [...prev, userMessage]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await askCopilotApi(q);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: res.answer,
          citations: res.citations || [],
          confidence: res.confidence || 'high',
          unverified: res.unverified || false,
          tools_used: res.tools_used || [],
          mode: res.mode || 'fallback',
          fallback_reason: res.fallback_reason || null
        }
      ]);
    } catch (err) {
      const errMsg = err.response?.data?.detail || err.message || "Evidentiary query processing error.";
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: `Evidentiary query error: ${errMsg}`,
          citations: [],
          confidence: 'low',
          unverified: true,
          tools_used: [],
          mode: 'fallback',
          fallback_reason: err.response?.status === 401 ? 'auth_error' : (err.response?.status === 429 ? 'rate_limit' : 'network')
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Helper to parse citations in text and render them as interactive chips
  const renderMessageText = (text) => {
    const parts = text.split(/(\[[A-Z0-9-]+\])/g);
    return parts.map((part, idx) => {
      const match = part.match(/\[([A-Z0-9-]+)\]/);
      if (match) {
        const eid = match[1];
        return (
          <button
            key={idx}
            onClick={() => setSelectedEvidence(eid)}
            className="inline-flex items-center font-mono font-bold text-[11px] text-teal-300 bg-teal-500/15 border border-teal-500/30 px-1.5 py-0.2 mx-0.5 rounded hover:bg-teal-500/30 transition align-baseline"
          >
            {part}
          </button>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 max-w-5xl mx-auto w-full p-4 lg:p-6 overflow-hidden">
      {/* Evidence Drawer Modal */}
      <EvidenceModal evidenceId={selectedEvidence} onClose={() => setSelectedEvidence(null)} />

      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 lg:p-5 shadow-xl flex items-center justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-teal-600 flex items-center justify-center text-white shadow-lg shadow-purple-950/60">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-100 flex items-center gap-2">
              Ask the Graph (Evidentiary Copilot)
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30">
                EVIDENCE CITATIONS ANCHORED
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Query the case knowledge base. Answers include direct clickable citations into official FIR, CDR, and toll logs.
            </p>
          </div>
        </div>

        <button
          onClick={() => setMessages([messages[0]])}
          title="Reset conversation transcript"
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Suggested Question Chips */}
      <div className="mb-4 flex-shrink-0">
        <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
          <Sparkles className="w-3 h-3 text-amber-400" />
          Suggested Investigative Queries
        </div>
        <div className="flex items-center gap-2 overflow-x-auto pb-1.5">
          {SUGGESTED_QUESTIONS.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(q)}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:border-teal-500/50 hover:text-teal-200 transition whitespace-nowrap flex-shrink-0"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Messages Transcript */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-4 select-text">
        {messages.map((m, idx) => {
          const isUser = m.role === 'user';
          return (
            <div
              key={idx}
              className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              {!isUser && (
                <div className="w-8 h-8 rounded-lg bg-purple-900/40 border border-purple-700/60 flex items-center justify-center text-purple-300 flex-shrink-0 mt-0.5">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-2xl rounded-2xl p-4 shadow-lg text-xs leading-relaxed ${
                  isUser
                    ? 'bg-teal-600 text-slate-950 font-medium'
                    : 'bg-slate-900 border border-slate-800 text-slate-200'
                }`}
              >
                {!isUser && (
                  <div className="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-slate-800/80 flex-wrap">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-red-400 flex items-center gap-1 font-heading">
                        <ShieldCheck className="w-3.5 h-3.5 text-red-500" />
                        Cited Answer
                      </span>
                      {m.mode === 'groq' ? (
                        <span className="px-1.5 py-0.5 rounded text-[9px] uppercase font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-700/60 flex items-center gap-1">
                          <Sparkles className="w-2.5 h-2.5 text-emerald-400" />
                          GROQ AI
                        </span>
                      ) : m.mode === 'fallback' ? (
                        <span className="px-1.5 py-0.5 rounded text-[9px] uppercase font-mono font-bold bg-amber-950/80 text-amber-300 border border-amber-700/60 flex items-center gap-1">
                          FALLBACK
                          {m.fallback_reason && (
                            <span className="font-mono text-amber-400 lowercase text-[9px] font-normal">
                              reason: {m.fallback_reason}
                            </span>
                          )}
                        </span>
                      ) : null}
                      {m.unverified && (
                        <span className="px-1.5 py-0.5 rounded text-[9px] uppercase font-mono font-bold bg-rose-950 text-rose-300 border border-rose-800">
                          Unverified
                        </span>
                      )}
                    </div>
                    {m.confidence && (
                      <span className={`px-1.5 py-0.2 rounded text-[9px] uppercase font-mono font-bold ${
                        m.confidence === 'high' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                        m.confidence === 'medium' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                        'bg-slate-800 text-slate-400'
                      }`}>
                        {m.confidence} Confidence
                      </span>
                    )}
                  </div>
                )}

                <div className="whitespace-pre-wrap">
                  {isUser ? m.text : renderMessageText(m.text)}
                </div>

                {!isUser && m.tools_used && m.tools_used.length > 0 && (
                  <div className="mt-2 text-[10px] font-mono text-slate-400 flex items-center gap-1.5 flex-wrap">
                    <span className="text-slate-400">Tools:</span>
                    {m.tools_used.map((t) => (
                      <span key={t} className="bg-slate-800/80 px-1.5 py-0.5 rounded text-slate-300">
                        {t}
                      </span>
                    ))}
                  </div>
                )}

                {!isUser && m.citations && m.citations.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center gap-1.5 flex-wrap">
                    <span className="text-[10px] font-mono text-slate-400">Referenced Evidence:</span>
                    {m.citations.map((c) => (
                      <button
                        key={c}
                        onClick={() => setSelectedEvidence(c)}
                        className="font-mono text-[10px] text-teal-300 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 hover:border-teal-500 transition"
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex gap-3 items-center text-xs text-slate-400 animate-pulse">
            <div className="w-8 h-8 rounded-lg bg-purple-900/40 border border-purple-700/60 flex items-center justify-center text-purple-300">
              <Bot className="w-4 h-4 animate-spin" />
            </div>
            <span>Evaluating graph topology & indexing evidentiary citations...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="flex-shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="relative flex items-center"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask anything about the Durg Missing Cluster (e.g. broker node, burner proximity, accounts)..."
            className="w-full pl-4 pr-12 py-3 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-teal-500 shadow-2xl transition"
          />
          <button
            type="submit"
            disabled={!inputQuery.trim() || loading}
            className="absolute right-2 p-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-slate-950 transition disabled:opacity-40"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default AskCopilot;
