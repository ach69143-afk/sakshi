import React, { useState, useEffect, useRef, useMemo } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import { 
  Filter, 
  Layers, 
  Play, 
  Pause, 
  RotateCcw, 
  Scissors, 
  ShieldAlert, 
  Info, 
  Calendar, 
  Sliders, 
  Eye, 
  Zap, 
  Maximize2, 
  HelpCircle,
  Share2,
  X,
  Compass,
  ArrowRight
} from 'lucide-react';
import { 
  getGraphApi, 
  getEntityApi, 
  explainEdgeApi, 
  simulateRemoveNodeApi, 
  getTimelineRangeApi 
} from '../api';
import { useAuth } from '../context/AuthContext';
import EvidenceModal from '../components/EvidenceModal';

const COMMUNITY_COLORS = {
  1: '#ef2b2d', // Bright Red (Core Bridge / Cluster 1)
  2: '#f97316', // Orange (Cluster 2)
  3: '#e8eaed', // White / Platinum (Cluster 3)
  4: '#94a3b8', // Slate Grey (Cluster 4)
  5: '#64748b', // Muted Grey (Cluster 5)
  6: '#cbd5e1', // Light Silver (Cluster 6)
};

const EDGE_COLORS = {
  call: '#ef2b2d',
  transfer: '#f97316',
  stay: '#94a3b8',
  co_travel: '#e8eaed',
  owns: '#64748b',
  mention: '#475569',
  ad_response: '#dc2626',
};

export const Network = () => {
  const { user, hasRole } = useAuth();
  const cyRef = useRef(null);

  // Data states
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(true);

  // Selection states
  const [selectedNode, setSelectedNode] = useState(null);
  const [entityDetails, setEntityDetails] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [edgeExplanation, setEdgeExplanation] = useState(null);
  const [selectedEvidence, setSelectedEvidence] = useState(null);

  // Simulation states
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [removedNodeId, setRemovedNodeId] = useState(null);

  // Shortest path mode
  const [pathMode, setPathMode] = useState(false);
  const [pathNodes, setPathNodes] = useState([]);

  // Filter states
  const [minScore, setMinScore] = useState(0.0);
  const [edgeTypeFilter, setEdgeTypeFilter] = useState({
    call: true,
    transfer: true,
    stay: true,
    co_travel: true,
    owns: true,
    mention: true,
    ad_response: true,
  });
  const [alertOnly, setAlertOnly] = useState(false);

  // Timeline states
  const [timelineRange, setTimelineRange] = useState({ start: '2026-09-01', end: '2026-09-30' });
  const [currentDate, setCurrentDate] = useState('2026-09-30');
  const [isPlaying, setIsPlaying] = useState(false);

  // Fetch initial graph
  useEffect(() => {
    const init = async () => {
      try {
        const [gData, tRange] = await Promise.all([
          getGraphApi(),
          getTimelineRangeApi()
        ]);
        setNodes(gData.nodes || []);
        setEdges(gData.edges || []);
        if (tRange) {
          setTimelineRange(tRange);
          setCurrentDate(tRange.end);
        }
      } catch (err) {
        console.error("Graph initialization error:", err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [user?.role]);

  // Handle timeline time scrubber change
  const handleTimelineChange = async (dateStr) => {
    setCurrentDate(dateStr);
    try {
      const gData = await getGraphApi(dateStr + "T23:59:59Z");
      setEdges(gData.edges || []);
    } catch (err) {
      console.error("Timeline filter error:", err);
    }
  };

  // Timeline play loop
  useEffect(() => {
    let timer = null;
    if (isPlaying) {
      timer = setInterval(() => {
        setCurrentDate(prev => {
          const startDay = 1;
          const endDay = 30;
          const curr = parseInt(prev.split('-')[2], 10);
          if (curr >= endDay) {
            setIsPlaying(false);
            return prev;
          }
          const nextDay = String(curr + 1).padStart(2, '0');
          const nextDate = `2026-09-${nextDay}`;
          handleTimelineChange(nextDate);
          return nextDate;
        });
      }, 700);
    }
    return () => clearInterval(timer);
  }, [isPlaying]);

  // Cytoscape elements mapping
  const elements = useMemo(() => {
    // Filter edges
    const activeEdges = edges.filter(e => {
      if (e.score < minScore) return false;
      if (!edgeTypeFilter[e.type]) return false;
      return true;
    });

    const activeNodeIds = new Set();
    activeEdges.forEach(e => {
      activeNodeIds.add(e.source);
      activeNodeIds.add(e.target);
    });

    const activeNodes = nodes.filter(n => {
      if (removedNodeId && n.id === removedNodeId) return false;
      if (alertOnly) {
        return (n.priority >= 0.75) && (activeNodeIds.has(n.id) || n.priority > 0.85);
      }
      return true;
    });

    const cyNodes = activeNodes.map(n => {
      const isBroker = n.is_broker || (n.betweenness && n.betweenness > 0.3) || n.id === 'ENT-R0019' || n.priority > 0.85;
      const isBurner = n.role_label?.toLowerCase().includes('burner') || n.type === 'phone' && n.priority > 0.8;
      const isMissing = n.type === 'person' && (n.id.startsWith('MP-') || n.role_label?.toLowerCase().includes('missing'));
      const isDecoy = n.role_label?.toLowerCase().includes('decoy') || n.id === 'ENT-R0022';
      const isAlert = n.priority >= 0.85;

      let componentColor = COMMUNITY_COLORS[n.community] || '#94a3b8';
      if (isBroker) componentColor = '#ef2b2d';
      else if (simResult && removedNodeId) {
        if (n.community === 1) componentColor = '#ef2b2d';
        else if (n.community === 2) componentColor = '#f97316';
        else componentColor = '#64748b';
      }

      // Clamp node size to 16-44 px based on priority
      const clampedSize = Math.max(16, Math.min(44, 16 + (n.priority || 0) * 28));
      // Truncate label to 14 chars
      const rawLabel = n.label || n.id || '';
      const truncatedLabel = rawLabel.length > 14 ? rawLabel.slice(0, 14) + '…' : rawLabel;

      return {
        data: {
          id: n.id,
          label: truncatedLabel,
          full_label: rawLabel,
          type: n.type,
          priority: n.priority,
          role_label: n.role_label,
          community: n.community,
          color: componentColor,
          size: clampedSize,
          isBroker,
          isBurner,
          isMissing,
          isDecoy,
          isAlert,
          borderWidth: isBroker ? 3.5 : isDecoy ? 2.5 : isAlert ? 2 : 1,
          borderColor: isBroker ? '#ef2b2d' : isDecoy ? '#f59e0b' : isAlert ? '#f87171' : '#2b1416'
        }
      };
    });

    const cyEdges = activeEdges.map(e => ({
      data: {
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.type,
        score: e.score,
        edge_kind: e.edge_kind,
        width: Math.max(1, Math.min(4, (e.score || 0.5) * 4)),
        lineStyle: e.edge_kind === 'observed' ? 'solid' : e.edge_kind === 'inferred' ? 'dashed' : 'dotted',
        color: EDGE_COLORS[e.type] || '#475569'
      }
    }));

    return [...cyNodes, ...cyEdges];
  }, [nodes, edges, minScore, edgeTypeFilter, alertOnly, removedNodeId, simResult]);

  // Fit to screen on load and after filters
  useEffect(() => {
    if (cyRef.current) {
      const cy = cyRef.current;
      const timer = setTimeout(() => {
        try {
          cy.layout(layoutConfig).run();
          cy.fit(undefined, 35);
        } catch (e) {}
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [minScore, edgeTypeFilter, alertOnly, removedNodeId, currentDate]);

  // Setup cytoscape event listeners
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;

    // Node click
    const handleNodeTap = async (evt) => {
      const node = evt.target;
      const nodeId = node.id();

      if (pathMode) {
        setPathNodes(prev => {
          if (prev.length === 0) return [nodeId];
          if (prev.length === 1) {
            const startId = prev[0];
            const endId = nodeId;
            // Compute shortest path with aStar or dijkstra
            const aStar = cy.elements().aStar({ root: `#${startId}`, goal: `#${endId}`, directed: false });
            if (aStar.found) {
              cy.elements().removeClass('highlighted muted');
              cy.elements().addClass('muted');
              aStar.path.removeClass('muted').addClass('highlighted');
            }
            return [startId, endId];
          }
          cy.elements().removeClass('highlighted muted');
          return [nodeId];
        });
        return;
      }

      setSelectedEdge(null);
      setEdgeExplanation(null);
      setSelectedNode(node.data());

      try {
        const details = await getEntityApi(nodeId);
        setEntityDetails(details);
      } catch (err) {
        console.error("Entity details fetch error:", err);
      }
    };

    // Edge click
    const handleEdgeTap = async (evt) => {
      const edge = evt.target;
      const src = edge.data('source');
      const tgt = edge.data('target');
      setSelectedNode(null);
      setEntityDetails(null);
      setSelectedEdge(edge.data());

      try {
        const exp = await explainEdgeApi(src, tgt);
        setEdgeExplanation(exp);
      } catch (err) {
        console.error("Edge explain fetch error:", err);
      }
    };

    cy.on('tap', 'node', handleNodeTap);
    cy.on('tap', 'edge', handleEdgeTap);

    return () => {
      cy.removeListener('tap');
    };
  }, [pathMode, user?.role]);

  // Layout configuration
  const layoutConfig = {
    name: 'cose',
    animate: true,
    animationDuration: 600,
    nodeRepulsion: 750000,
    idealEdgeLength: 90,
    edgeElasticity: 100,
    nestingFactor: 1.2,
    gravity: 0.25,
    numIter: 400,
  };

  // Cytoscape stylesheet
  const stylesheet = [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'width': 'data(size)',
        'height': 'data(size)',
        'background-color': 'data(color)',
        'border-width': 'data(borderWidth)',
        'border-color': 'data(borderColor)',
        'color': '#f8fafc',
        'font-size': '10px',
        'font-family': 'Inter, sans-serif',
        'text-valign': 'bottom',
        'text-margin-y': 6,
        'text-background-opacity': 0.85,
        'text-background-color': '#0b111e',
        'text-background-padding': '3px',
        'text-background-shape': 'roundrectangle',
        'text-border-opacity': 0.5,
        'text-border-width': 1,
        'text-border-color': '#1e293b',
        'transition-property': 'background-color, line-color, target-arrow-color, opacity, width, height',
        'transition-duration': '0.4s'
      }
    },
    {
      selector: 'node[isBroker]',
      style: {
        'shape': 'diamond',
        'background-color': '#ef2b2d',
        'border-color': '#ffffff',
        'border-width': 3,
        'shadow-blur': 25,
        'shadow-color': '#ef2b2d',
        'shadow-opacity': 0.9,
      }
    },
    {
      selector: 'node[isDecoy]',
      style: {
        'border-color': '#f59e0b',
        'border-width': 2.5,
        'border-style': 'dashed',
      }
    },
    {
      selector: 'node[isBurner]',
      style: {
        'shape': 'hexagon',
        'shadow-blur': 20,
        'shadow-color': '#f59e0b',
        'shadow-opacity': 0.8,
      }
    },
    {
      selector: 'node[isMissing]',
      style: {
        'shape': 'round-rectangle',
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 'data(width)',
        'line-color': 'data(color)',
        'line-style': 'data(lineStyle)',
        'curve-style': 'bezier',
        'opacity': 0.75,
        'target-arrow-shape': 'triangle',
        'target-arrow-color': 'data(color)',
        'arrow-scale': 0.8,
      }
    },
    {
      selector: '.highlighted',
      style: {
        'opacity': 1,
        'line-color': '#2dd4bf',
        'target-arrow-color': '#2dd4bf',
        'shadow-blur': 15,
        'shadow-color': '#2dd4bf',
        'shadow-opacity': 0.9,
        'z-index': 999
      }
    },
    {
      selector: '.muted',
      style: {
        'opacity': 0.12,
      }
    }
  ];

  // Node Removal Simulation (Shatter Network)
  const handleSimulateRemoveNode = async (nodeId) => {
    if (!hasRole(['head_constable', 'cyber_cell', 'sp_dysp'])) return;
    setSimulating(true);
    try {
      const res = await simulateRemoveNodeApi(nodeId);
      setSimResult(res);
      setRemovedNodeId(nodeId);

      // Animate shattering in Cytoscape
      if (cyRef.current) {
        const cy = cyRef.current;
        const targetNode = cy.$(`#${nodeId}`);
        targetNode.animate({
          style: { opacity: 0, width: 2, height: 2 },
          duration: 500,
          complete: () => {
            cy.layout({ name: 'cose', animate: true, animationDuration: 700 }).run();
          }
        });
      }
    } catch (err) {
      console.error("Simulation error:", err);
    } finally {
      setSimulating(false);
    }
  };

  const handleRestoreNode = () => {
    setRemovedNodeId(null);
    setSimResult(null);
    if (cyRef.current) {
      cyRef.current.elements().removeClass('muted highlighted');
      setTimeout(() => {
        cyRef.current.layout({ name: 'cose', animate: true, animationDuration: 600 }).run();
      }, 100);
    }
  };

  const resetPathHighlight = () => {
    setPathMode(false);
    setPathNodes([]);
    if (cyRef.current) {
      cyRef.current.elements().removeClass('muted highlighted');
    }
  };

  const canSimulate = hasRole(['head_constable', 'cyber_cell', 'sp_dysp']);

  return (
    <div className="flex-1 flex flex-col h-full relative overflow-hidden bg-slate-950">
      {/* Evidence Modal */}
      <EvidenceModal evidenceId={selectedEvidence} onClose={() => setSelectedEvidence(null)} />

      {/* Top Filter & Control Strip */}
      <div className="h-12 bg-slate-900 border-b border-slate-800 px-4 flex items-center justify-between text-xs z-10 flex-shrink-0 select-none">
        <div className="flex items-center gap-3 overflow-x-auto py-1">
          {/* Min Score slider */}
          <div className="flex items-center gap-2 pr-3 border-r border-slate-800">
            <span className="text-slate-400 font-mono text-[11px]">Min Score:</span>
            <input
              type="range"
              min="0"
              max="0.95"
              step="0.05"
              value={minScore}
              onChange={(e) => setMinScore(parseFloat(e.target.value))}
              className="w-20 accent-teal-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
            />
            <span className="font-mono text-teal-300 font-bold w-7 text-right">
              {minScore.toFixed(2)}
            </span>
          </div>

          {/* Edge Type Filters */}
          <div className="flex items-center gap-1.5 pr-3 border-r border-slate-800">
            {Object.keys(edgeTypeFilter).map((type) => (
              <button
                key={type}
                onClick={() => setEdgeTypeFilter(prev => ({ ...prev, [type]: !prev[type] }))}
                className={`px-2 py-0.5 rounded text-[10px] font-mono transition uppercase ${
                  edgeTypeFilter[type]
                    ? 'bg-slate-800 text-slate-200 border border-slate-700 font-semibold'
                    : 'bg-slate-950 text-slate-600 border border-slate-900 line-through'
                }`}
                style={{
                  borderLeftColor: edgeTypeFilter[type] ? EDGE_COLORS[type] : undefined,
                  borderLeftWidth: edgeTypeFilter[type] ? '3px' : undefined
                }}
              >
                {type}
              </button>
            ))}
          </div>

          {/* Alert only toggle */}
          <button
            onClick={() => setAlertOnly(!alertOnly)}
            className={`px-2.5 py-1 rounded text-[11px] font-semibold transition flex items-center gap-1.5 ${
              alertOnly
                ? 'bg-rose-950 text-rose-300 border border-rose-800'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
            <span>Alerts Only</span>
          </button>
        </div>

        {/* Action buttons right */}
        <div className="flex items-center gap-2">
          {/* Shortest Path Mode */}
          <button
            onClick={() => {
              if (pathMode) resetPathHighlight();
              else {
                setPathMode(true);
                setPathNodes([]);
              }
            }}
            className={`px-2.5 py-1 rounded text-[11px] font-semibold border transition flex items-center gap-1.5 ${
              pathMode
                ? 'bg-teal-950 text-teal-300 border-teal-500 animate-pulse'
                : 'bg-slate-800 text-slate-300 border-slate-700 hover:text-white'
            }`}
          >
            <Compass className="w-3.5 h-3.5 text-teal-400" />
            <span>{pathMode ? (pathNodes.length === 1 ? 'Click Target Node' : 'Exit Path Mode') : 'Find Shortest Path'}</span>
          </button>

          {/* Reset Layout */}
          <button
            onClick={() => {
              if (cyRef.current) {
                cyRef.current.layout(layoutConfig).run();
                cyRef.current.fit(undefined, 30);
              }
            }}
            title="Recenter and layout graph"
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Canvas + Panels */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Cytoscape Canvas */}
        <div className="flex-1 h-full w-full relative bg-slate-950">
          <CytoscapeComponent
            elements={elements}
            layout={layoutConfig}
            stylesheet={stylesheet}
            cy={(cy) => {
              if (cyRef.current !== cy) {
                cyRef.current = cy;
                setTimeout(() => {
                  try {
                    cy.layout(layoutConfig).run();
                    cy.fit(undefined, 40);
                  } catch (e) {}
                }, 150);
              }
            }}
            className="cytoscape-canvas-container"
          />

          {/* Community Legend overlay */}
          <div className="absolute bottom-16 left-4 bg-slate-900/90 border border-slate-800 rounded-xl p-3 shadow-xl backdrop-blur-sm text-[11px] space-y-1.5 select-none pointer-events-auto z-10 hidden sm:block">
            <div className="font-semibold text-slate-400 uppercase tracking-wider text-[10px] mb-1">
              Topological Clusters
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <span className="w-3 h-3 rounded-full bg-teal-500"></span>
              <span>Cluster A: Durg Local Logistics</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <span className="w-3 h-3 rounded-full bg-amber-500"></span>
              <span>Cluster B: Nagpur Receivers</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <span className="w-3 h-3 rotate-45 bg-pink-500"></span>
              <span className="font-semibold text-pink-300">Broker Articulation Point</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <span className="w-3 h-3 rounded-full bg-purple-500"></span>
              <span>Pass-through Rapid Relay Chain</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <span className="w-3 h-3 rounded-sm bg-sky-400"></span>
              <span>Missing Individuals Group</span>
            </div>
          </div>

          {/* Shatter Simulation Result Floating Card */}
          {simResult && (
            <div className="absolute top-4 left-4 max-w-sm bg-slate-900/95 border border-rose-500/50 rounded-2xl p-4 shadow-2xl backdrop-blur-md z-20 animate-fade-in">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Scissors className="w-4 h-4 text-rose-400" />
                  <span className="font-bold text-xs text-rose-300 uppercase tracking-wide">
                    Interdiction Shatter Simulation
                  </span>
                </div>
                <button 
                  onClick={handleRestoreNode}
                  className="text-xs text-slate-400 hover:text-slate-200 underline"
                >
                  Restore Node
                </button>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed mb-3">
                {simResult.explanation}
              </p>

              <div className="grid grid-cols-3 gap-2 p-2.5 bg-slate-950 rounded-xl border border-slate-800 text-center text-xs">
                <div>
                  <div className="text-slate-400 text-[10px] uppercase">Components</div>
                  <div className="font-mono font-bold text-slate-100">
                    {simResult.before.components} → <span className="text-rose-400 font-extrabold">{simResult.after.components}</span>
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 text-[10px] uppercase">Largest Hub</div>
                  <div className="font-mono font-bold text-slate-100">
                    {simResult.before.largest} → <span className="text-rose-400 font-extrabold">{simResult.after.largest}</span>
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 text-[10px] uppercase">Efficiency Δ</div>
                  <div className="font-mono font-bold text-rose-400 text-sm">
                    {simResult.delta_pct}%
                  </div>
                </div>
              </div>

              <button
                onClick={handleRestoreNode}
                className="w-full mt-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition"
              >
                Reset Network State
              </button>
            </div>
          )}
        </div>

        {/* Right Inspector Panel: Entity or Edge Explanation */}
        {(selectedNode || selectedEdge) && (
          <div className="w-80 md:w-96 bg-slate-900 border-l border-slate-800 flex flex-col justify-between shadow-2xl z-20 overflow-y-auto">
            {/* Header */}
            <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60 sticky top-0 z-10 backdrop-blur-sm">
              <span className="text-xs font-bold uppercase tracking-wider text-teal-400 flex items-center gap-2">
                <Info className="w-4 h-4" />
                {selectedNode ? 'Entity Intelligence Dossier' : 'Edge Evidence Decomposition'}
              </span>
              <button
                onClick={() => {
                  setSelectedNode(null);
                  setSelectedEdge(null);
                  setEntityDetails(null);
                  setEdgeExplanation(null);
                }}
                className="p-1 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* NODE INSPECTOR CONTENT */}
            {selectedNode && (
              <div className="p-5 space-y-4 flex-1">
                {/* Node Title & Tags */}
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-teal-300 font-bold border border-slate-700">
                      {selectedNode.id}
                    </span>
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      {selectedNode.type}
                    </span>
                  </div>
                  <h2 className="text-base font-bold text-slate-100">{selectedNode.label}</h2>
                  <div className="text-xs text-teal-300/90 font-medium mt-0.5">
                    {selectedNode.role_label}
                  </div>
                </div>

                {/* Priority Score & Breakdown */}
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 font-medium">Investigative Priority</span>
                    <span className="font-mono text-sm font-bold text-teal-400">
                      {(selectedNode.priority * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-teal-500 to-amber-500 h-full rounded-full transition-all duration-500"
                      style={{ width: `${selectedNode.priority * 100}%` }}
                    ></div>
                  </div>

                  {entityDetails?.priority_breakdown && (
                    <div className="pt-2 grid grid-cols-2 gap-2 text-[10px] text-slate-400 border-t border-slate-800/80">
                      <div>
                        Betweenness: <span className="font-mono text-slate-200">{entityDetails.priority_breakdown.betweenness}</span>
                      </div>
                      <div>
                        PageRank: <span className="font-mono text-slate-200">{entityDetails.priority_breakdown.pagerank}</span>
                      </div>
                      <div>
                        Cross-Cluster: <span className="font-mono text-slate-200">{entityDetails.priority_breakdown.cross_community}</span>
                      </div>
                      <div>
                        Evidence Div: <span className="font-mono text-slate-200">{entityDetails.priority_breakdown.evidence_diversity}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Aliases */}
                {selectedNode.aliases && selectedNode.aliases.length > 0 && (
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                      Identified Aliases
                    </label>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedNode.aliases.map((al, idx) => (
                        <span key={idx} className="text-xs px-2 py-0.5 rounded bg-slate-800/80 text-amber-300 border border-slate-700 font-mono">
                          {al}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Phone (masking display) */}
                {selectedNode.phone && (
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                      Registered Cellular MSISDN
                    </label>
                    <div className="font-mono text-xs text-slate-200 bg-slate-950 p-2 rounded border border-slate-800 flex items-center justify-between">
                      <span>{selectedNode.phone}</span>
                      {selectedNode.phone.includes('XXXXX') && (
                        <span className="text-[9px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                          Masked for {user?.role}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Evidentiary Citations */}
                {entityDetails?.evidence && (
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                      Direct Evidentiary Records
                    </label>
                    <div className="space-y-2">
                      {entityDetails.evidence.map((ev) => (
                        <div key={ev.evidence_id} className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1">
                          <div className="flex items-center justify-between">
                            <button
                              onClick={() => setSelectedEvidence(ev.evidence_id)}
                              className="font-mono text-[10px] text-teal-300 bg-teal-500/15 border border-teal-500/30 px-1.5 py-0.5 rounded hover:bg-teal-500/25 transition"
                            >
                              {ev.evidence_id}
                            </button>
                            <span className="text-[9px] uppercase px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">
                              {ev.kind}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-300 leading-snug">
                            {ev.summary}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* SIMULATE REMOVE NODE BUTTON (RBAC PROTECTED) */}
                <div className="pt-2 border-t border-slate-800">
                  <div className="relative group">
                    <button
                      onClick={() => handleSimulateRemoveNode(selectedNode.id)}
                      disabled={!canSimulate || simulating}
                      className={`w-full py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition ${
                        canSimulate
                          ? 'bg-rose-950 hover:bg-rose-900 text-rose-200 border border-rose-700 shadow-lg'
                          : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed opacity-60'
                      }`}
                    >
                      <Scissors className="w-4 h-4 text-rose-400" />
                      <span>{simulating ? 'Calculating Topology...' : 'Simulate Node Removal (Interdiction)'}</span>
                    </button>
                    {!canSimulate && (
                      <div className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-slate-800 border border-slate-700 text-[10px] text-slate-300 rounded shadow-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition pointer-events-none">
                        Not permitted for {user?.role}. Requires Head Constable or higher.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* EDGE INSPECTOR "WHY" PANEL */}
            {selectedEdge && (
              <div className="p-5 space-y-4 flex-1">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-amber-300 font-bold border border-slate-700">
                      {selectedEdge.source} ➔ {selectedEdge.target}
                    </span>
                    <span className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded ${
                      selectedEdge.edge_kind === 'observed' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                      selectedEdge.edge_kind === 'extracted' ? 'bg-sky-950 text-sky-300 border border-sky-800' :
                      'bg-amber-950 text-amber-300 border border-amber-800'
                    }`}>
                      {selectedEdge.edge_kind}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">
                    Association Confidence: {((selectedEdge.score || 0.85) * 100).toFixed(0)}%
                  </h3>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    Modality: <span className="font-mono text-teal-300 uppercase">{selectedEdge.type}</span>
                  </div>
                </div>

                {/* Score Formula */}
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
                    Probabilistic Synthesis Formula
                  </div>
                  <div className="font-mono text-xs text-teal-300 font-bold">
                    {edgeExplanation?.formula || '1 - prod(1 - w*s)'}
                  </div>
                </div>

                {/* Component Breakdown Bars */}
                {edgeExplanation?.components && (
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
                      Component Weight Contribution
                    </label>
                    <div className="space-y-2">
                      {edgeExplanation.components.map((c, idx) => (
                        <div key={idx} className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-xs space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-slate-200 capitalize">{c.type.replace('_', ' ')} ({c.count} instances)</span>
                            <span className="font-mono font-bold text-amber-400">+{c.contribution}</span>
                          </div>
                          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                            <div className="bg-amber-500 h-full rounded-full" style={{ width: `${Math.min(100, c.contribution * 200)}%` }}></div>
                          </div>
                          <div className="flex items-center gap-1 flex-wrap pt-1">
                            <span className="text-[9px] text-slate-500">Citations:</span>
                            {c.evidence_ids.map(eid => (
                              <button
                                key={eid}
                                onClick={() => setSelectedEvidence(eid)}
                                className="font-mono text-[9px] text-teal-300 bg-slate-800 px-1.5 py-0.2 rounded hover:bg-slate-700"
                              >
                                {eid}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* FIR & CDR Verbatim Snippets */}
                {edgeExplanation?.snippets && (
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                      Corroborating Case Extract
                    </label>
                    <div className="space-y-2">
                      {edgeExplanation.snippets.map((sn, idx) => (
                        <div key={idx} className="p-3 bg-slate-950 rounded-lg border border-slate-800 font-mono text-[11px] leading-relaxed text-slate-300">
                          <button
                            onClick={() => setSelectedEvidence(sn.evidence_id)}
                            className="font-bold text-teal-300 hover:underline mr-1.5"
                          >
                            [{sn.evidence_id}]
                          </button>
                          <span>{sn.text}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Timeline Range Scrubber */}
      <div className="h-14 bg-slate-900 border-t border-slate-800 px-4 lg:px-6 flex items-center justify-between text-xs z-10 flex-shrink-0 select-none">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="w-8 h-8 rounded-lg bg-teal-600 hover:bg-teal-500 text-slate-950 flex items-center justify-center transition shadow-md"
          >
            {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
          </button>

          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-teal-400" />
            <span className="text-slate-400 hidden sm:inline">Temporal Cutoff:</span>
            <span className="font-mono font-bold text-teal-300 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
              {currentDate}
            </span>
          </div>
        </div>

        {/* Slider Input */}
        <div className="flex-1 max-w-xl mx-4">
          <div className="relative flex items-center">
            <input
              type="range"
              min="1"
              max="30"
              value={parseInt(currentDate.split('-')[2], 10) || 30}
              onChange={(e) => {
                const day = String(e.target.value).padStart(2, '0');
                handleTimelineChange(`2026-09-${day}`);
              }}
              className="w-full accent-teal-500 h-2 bg-slate-800 rounded-lg cursor-pointer"
            />
          </div>
          <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-1">
            <span>{timelineRange.start}</span>
            <span>Mid-Investigation Wave</span>
            <span>{timelineRange.end}</span>
          </div>
        </div>

        <div className="text-[11px] font-mono text-slate-400 hidden md:block">
          Active Edges: <span className="text-teal-300 font-bold">{edges.length}</span>
        </div>
      </div>
    </div>
  );
};

export default Network;
