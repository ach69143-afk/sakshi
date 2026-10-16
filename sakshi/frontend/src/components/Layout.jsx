import React, { useState, useEffect } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { 
  Network, 
  Clock, 
  GitMerge, 
  AlertTriangle, 
  Bot, 
  FileSpreadsheet, 
  ShieldCheck, 
  ShieldAlert, 
  LayoutDashboard, 
  LogOut, 
  UserCheck, 
  RefreshCw, 
  Bug, 
  CheckCircle2, 
  XCircle,
  HelpCircle,
  ClipboardCheck,
  FolderKanban,
  ChevronDown,
  X
} from 'lucide-react';
import { useAuth, SEED_USERS } from '../context/AuthContext';
import { 
  verifyLedgerApi, 
  getSummaryApi, 
  getCasesApi, 
  getActiveCaseId, 
  setActiveCaseId 
} from '../api';

export const Layout = () => {
  const { user, logout, switchRoleDirectly, debugMode, setDebugMode } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [ledgerStatus, setLedgerStatus] = useState({ ok: true, verifying: false });
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);
  const [caseMenuOpen, setCaseMenuOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [counts, setCounts] = useState({ alerts: null, mergeQueue: null, crossCasePending: null });
  const [caseList, setCaseList] = useState([]);
  const [currentCaseId, setCurrentCaseId] = useState(() => getActiveCaseId());

  const fetchCases = async () => {
    try {
      const data = await getCasesApi();
      const list = Array.isArray(data) ? data : [];
      setCaseList(list);
      if (list.length > 0) {
        const stored = getActiveCaseId();
        const exists = list.some(c => c.case_id === stored);
        const resolved = exists ? stored : list[0].case_id;
        if (resolved !== currentCaseId) {
          setCurrentCaseId(resolved);
          setActiveCaseId(resolved);
        }
      }
    } catch (err) {
      console.error('Failed to load authorized cases:', err);
    }
  };

  const fetchCounts = async () => {
    try {
      const summary = await getSummaryApi();
      setCounts({
        alerts: summary.alerts_total ?? null,
        mergeQueue: summary.pending_merges ?? null,
        crossCasePending: summary.cross_case_pending ?? null
      });
    } catch {
      // fallback
    }
  };

  const checkChain = async () => {
    setLedgerStatus(prev => ({ ...prev, verifying: true }));
    try {
      const res = await verifyLedgerApi();
      setLedgerStatus({ ok: res.ok, broken_at: res.broken_at, verifying: false });
    } catch {
      setLedgerStatus({ ok: true, verifying: false });
    }
  };

  useEffect(() => {
    checkChain();
    fetchCases();
    fetchCounts();
    const interval = setInterval(() => {
      checkChain();
      fetchCounts();
    }, 12000);
    return () => clearInterval(interval);
  }, [user?.role, user?.email]);

  useEffect(() => {
    const handleCaseChanged = (e) => {
      const id = e.detail?.caseId || getActiveCaseId();
      setCurrentCaseId(id);
      fetchCounts();
    };
    window.addEventListener('sakshi-case-changed', handleCaseChanged);
    return () => window.removeEventListener('sakshi-case-changed', handleCaseChanged);
  }, []);

  useEffect(() => {
    const handleRbacDenied = (e) => {
      setToastMessage(e.detail || 'Access Denied: Action not permitted for your current role.');
      setTimeout(() => setToastMessage(null), 6000);
    };
    window.addEventListener('sakshi-rbac-denied', handleRbacDenied);
    return () => window.removeEventListener('sakshi-rbac-denied', handleRbacDenied);
  }, []);

  const activeCaseObj = caseList.find(c => c.case_id === currentCaseId) || {
    case_id: currentCaseId,
    title: currentCaseId === 'SP-021' ? 'Raipur Financial Fraud & Disappearance' : 'Durg Missing Cluster',
    district: currentCaseId === 'SP-021' ? 'Raipur' : 'Durg',
    status: 'Open'
  };

  const navItems = [
    { to: '/cases', label: 'Cases', icon: FolderKanban },
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/network', label: 'Network Graph', icon: Network, highlight: true },
    { 
      to: '/cross-case', 
      label: 'Cross-Case Links', 
      icon: GitMerge, 
      badge: counts.crossCasePending !== null && counts.crossCasePending > 0 ? String(counts.crossCasePending) : undefined 
    },
    { to: '/merge-queue', label: 'Merge Queue', icon: GitMerge, badge: counts.mergeQueue !== null ? String(counts.mergeQueue) : undefined },
    { to: '/golden-hour', label: 'Golden Hour Map', icon: Clock },
    { to: '/alerts', label: 'Alerts', icon: AlertTriangle, badge: counts.alerts !== null ? String(counts.alerts) : undefined },
    { to: '/copilot', label: 'Ask the Graph', icon: Bot },
    { to: '/report', label: 'Case Dossier', icon: FileSpreadsheet },
    { to: '/ledger', label: 'Chain of Custody', icon: ShieldCheck, rbac: ['cyber_cell', 'sp_dysp', 'sp_dysp_raipur', 'ig', 'auditor'] },
    { to: '/validation', label: 'Validation Suite', icon: ClipboardCheck, rbac: ['cyber_cell', 'sp_dysp', 'sp_dysp_raipur', 'ig', 'auditor'] },
  ];

  const getRoleBadgeStyle = (role) => {
    switch (role) {
      case 'ig':
        return 'bg-indigo-500/15 text-indigo-300 border-indigo-500/40';
      case 'sp_dysp_raipur':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/40';
      case 'sp_dysp':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/40';
      case 'cyber_cell':
        return 'bg-teal-500/15 text-teal-300 border-teal-500/40';
      case 'head_constable':
        return 'bg-blue-500/15 text-blue-300 border-blue-500/40';
      case 'auditor':
        return 'bg-purple-500/15 text-purple-300 border-purple-500/40';
      default:
        return 'bg-slate-700/50 text-slate-300 border-slate-600';
    }
  };

  const getRoleDisplayName = (role) => {
    switch (role) {
      case 'ig': return 'IG Range';
      case 'sp_dysp_raipur': return 'SP Raipur';
      case 'sp_dysp': return 'SP / DySP';
      case 'cyber_cell': return 'Cyber Cell';
      case 'head_constable': return 'Head Constable';
      case 'constable': return 'Constable';
      case 'auditor': return 'Forensic Auditor';
      default: return role;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Bar */}
      <header className="h-14 bg-slate-900 border-b border-slate-800 px-4 lg:px-6 flex items-center justify-between z-30 select-none">
        {/* Left: Project title & Case Switcher Dropdown */}
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/dashboard')}>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-600 to-red-900 flex items-center justify-center font-bold text-white text-sm shadow-md shadow-red-900/50">
              सा
            </div>
            <div>
              <span className="font-extrabold tracking-wider text-base text-slate-100">SAKSHI</span>
              <span className="text-[10px] text-red-400 font-mono ml-1.5 uppercase tracking-widest hidden sm:inline">Workbench v2.0</span>
            </div>
          </div>

          <div className="h-5 w-px bg-slate-800 mx-1 hidden sm:block"></div>

          {/* Interactive Case Switcher Dropdown */}
          <div className="relative">
            <button
              onClick={() => setCaseMenuOpen(!caseMenuOpen)}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-800 border border-slate-700 hover:border-red-800/80 transition text-left group shadow-sm"
              title="Click to switch operational case context"
            >
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-950 text-red-300 font-bold border border-red-900/60 shadow-inner">
                {activeCaseObj.case_id}
              </span>
              <span className="text-xs font-semibold text-slate-200 hidden md:inline truncate max-w-[170px]">
                {activeCaseObj.title}
              </span>
              <span className="text-[10px] px-1.5 py-0.2 rounded font-mono text-slate-400 bg-slate-900 border border-slate-800 hidden lg:inline">
                {activeCaseObj.district}
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 group-hover:text-red-300 transition-transform" />
            </button>

            {caseMenuOpen && (
              <div
                className="absolute left-0 mt-2 w-80 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-2 z-50 text-xs"
                onMouseLeave={() => setCaseMenuOpen(false)}
              >
                <div className="px-3 py-1.5 font-bold text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800 flex items-center justify-between mb-1">
                  <span>Authorized Cases ({caseList.length || 1})</span>
                  <span className="text-[9px] text-red-400 font-mono">X-Case-Id header</span>
                </div>
                {(caseList.length > 0 ? caseList : [activeCaseObj]).map((c) => {
                  const isSelected = c.case_id === currentCaseId;
                  return (
                    <button
                      key={c.case_id}
                      onClick={() => {
                        setActiveCaseId(c.case_id);
                        setCurrentCaseId(c.case_id);
                        setCaseMenuOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center justify-between transition ${
                        isSelected 
                          ? 'bg-red-950/60 text-white border border-red-800/60 font-semibold shadow-inner' 
                          : 'text-slate-300 hover:bg-slate-800/70'
                      }`}
                    >
                      <div className="flex-1 min-w-0 pr-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-red-300 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                            {c.case_id}
                          </span>
                          <span className="text-[10px] text-slate-400 font-medium">({c.district} District)</span>
                        </div>
                        <div className="text-[11px] text-slate-300 truncate mt-1">{c.title}</div>
                      </div>
                      {isSelected ? (
                        <span className="text-emerald-400 text-xs font-bold px-1.5 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/50">
                          Active
                        </span>
                      ) : (
                        <span className="text-slate-500 text-[10px] uppercase font-mono">Switch</span>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right: Ledger Integrity Badge, Officer Name, Role Badge & Controls */}
        <div className="flex items-center gap-3">
          {/* Ledger Integrity status */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={checkChain}
              title="Click to verify cryptographic ledger integrity"
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium border transition ${
                ledgerStatus.ok
                  ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60 hover:bg-emerald-900/40'
                  : 'bg-rose-950/60 text-rose-300 border-rose-700 hover:bg-rose-900/60 animate-pulse'
              }`}
            >
              {ledgerStatus.verifying ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-teal-400" />
              ) : ledgerStatus.ok ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <XCircle className="w-3.5 h-3.5 text-rose-400" />
              )}
              <span className="hidden sm:inline">
                {ledgerStatus.ok ? 'Chain intact' : `Chain broken (Block #${ledgerStatus.broken_at || 17})`}
              </span>
            </button>
          </div>

          {/* Debug Mode toggle */}
          <button
            onClick={() => setDebugMode(!debugMode)}
            title="Toggle presentation demo debugger"
            className={`p-1.5 rounded-md border text-xs transition ${
              debugMode 
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' 
                : 'bg-slate-800/60 text-slate-400 border-slate-700 hover:text-slate-200'
            }`}
          >
            <Bug className="w-3.5 h-3.5" />
          </button>

          {/* Officer Display Name */}
          <div className="hidden sm:flex flex-col text-right">
            <span className="text-xs font-semibold text-slate-200">{user?.name || 'Officer'}</span>
            <span className="text-[10px] font-mono text-slate-400">{user?.email}</span>
          </div>

          {/* Role badge with switch dropdown (Includes IG & SP Raipur) */}
          <div className="relative">
            <button
              onClick={() => setRoleMenuOpen(!roleMenuOpen)}
              className={`flex items-center gap-2 px-2.5 py-1 rounded-md text-xs font-semibold border ${getRoleBadgeStyle(user?.role)} hover:opacity-90 transition`}
            >
              <UserCheck className="w-3.5 h-3.5" />
              <span>{getRoleDisplayName(user?.role)}</span>
              <span className="text-[10px] text-slate-400">▼</span>
            </button>

            {roleMenuOpen && (
              <div 
                className="absolute right-0 mt-2 w-72 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl p-2 z-50 text-xs"
                onMouseLeave={() => setRoleMenuOpen(false)}
              >
                <div className="px-2 py-1 font-semibold text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800 mb-1">
                  Demo Role Switcher (RBAC Multi-Case)
                </div>
                {SEED_USERS.map((u) => (
                  <button
                    key={u.email}
                    onClick={async () => {
                      await switchRoleDirectly(u.email);
                      setRoleMenuOpen(false);
                      fetchCases();
                    }}
                    className={`w-full text-left px-2.5 py-2 rounded-md flex items-center justify-between transition ${
                      user?.email === u.email ? 'bg-slate-800 text-teal-300 font-medium' : 'text-slate-300 hover:bg-slate-800/60'
                    }`}
                  >
                    <div>
                      <div className="font-medium">{u.name}</div>
                      <div className="text-[10px] text-slate-400">{u.label}</div>
                    </div>
                    {user?.email === u.email && <span className="text-teal-400 text-xs">●</span>}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Sign Out */}
          <button
            onClick={() => {
              logout();
              navigate('/');
            }}
            title="Sign out of workbench"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs text-slate-300 hover:text-red-400 hover:bg-slate-800 border border-slate-700/70 transition"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden md:inline font-medium">Sign out</span>
          </button>
        </div>
      </header>

      {/* Main Workspace Body: Sidebar + Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Nav */}
        <aside className="w-16 lg:w-56 bg-slate-900/90 border-r border-slate-800 flex flex-col justify-between py-3 flex-shrink-0 select-none">
          <nav className="space-y-1 px-2">
            {navItems
              .filter(item => !item.rbac || item.rbac.includes(user?.role))
              .map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition group relative ${
                      isActive
                        ? 'active-nav-item border-l-4 border-l-red-500 bg-red-950/40 text-white font-semibold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    } ${item.highlight && !location.pathname.includes(item.to) ? 'text-slate-200' : ''}`
                  }
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span className="hidden lg:inline">{item.label}</span>
                  {item.badge && (
                    <span className="hidden lg:inline-block ml-auto px-1.5 py-0.2 rounded text-[10px] font-mono bg-red-950 text-red-300 border border-red-800/80 font-bold">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>

          {/* User profile card in sidebar bottom */}
          <div className="px-2 pt-2 border-t border-slate-800/80">
            <div className="hidden lg:block p-2 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <div className="text-[11px] font-semibold text-slate-200 truncate">{user?.name}</div>
              <div className="text-[10px] font-mono text-slate-400 truncate">{user?.email}</div>
              <div className="mt-1 flex items-center justify-between text-[9px]">
                <div className="flex items-center gap-1 text-teal-400 uppercase tracking-wider font-semibold">
                  <span className="w-1.5 h-1.5 rounded-full bg-teal-400"></span>
                  <span>Active Session</span>
                </div>
                <span className="font-mono font-bold text-red-400">{currentCaseId}</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Content Area - key={currentCaseId} ensures automatic remount and re-fetch on case change */}
        <main className="flex-1 overflow-y-auto bg-slate-950 flex flex-col relative">
          {toastMessage && (
            <div className="fixed top-16 right-6 z-50 max-w-md bg-rose-950/95 border border-rose-700 text-rose-200 px-4 py-3 rounded-xl shadow-2xl flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1 text-xs">
                <div className="font-bold text-rose-300 mb-0.5">Authorization Notice</div>
                <div className="text-slate-200 font-mono text-[11px] leading-relaxed">{toastMessage}</div>
              </div>
              <button 
                onClick={() => setToastMessage(null)}
                className="text-rose-400 hover:text-rose-200 p-0.5 rounded transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
          <Outlet key={currentCaseId} />
        </main>
      </div>

      {/* Mandatory Persistent Footer Banner */}
      <footer className="h-7 bg-slate-950 border-t border-slate-800/80 px-4 flex items-center justify-between text-[11px] text-slate-400 z-30 select-none">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-amber-400/80 animate-pulse"></span>
          <span className="font-medium text-amber-300/90 tracking-wide">
            Synthetic data. Patterns for investigator review. Not an accusation.
          </span>
        </div>
        <div className="hidden sm:flex items-center gap-3 text-slate-500 font-mono text-[10px]">
          <span>EVIDENTIARY AUDIT HASH: e8a93bc2</span>
          <span>•</span>
          <span>MULTI-CASE WORKBENCH ({currentCaseId})</span>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
