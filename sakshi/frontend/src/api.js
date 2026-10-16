import axios from 'axios';

// Resolve base URL from environment variable consistently
export const resolveBaseUrl = () => {
  const envUrl = (import.meta.env.VITE_API_URL || '').trim();
  if (!envUrl) {
    return '';
  }
  // Strip trailing slashes
  let cleanUrl = envUrl.replace(/\/+$/, '');
  // If the user specified a base URL that already includes /api, strip it
  // because all our endpoint paths explicitly include the /api prefix
  cleanUrl = cleanUrl.replace(/\/api$/, '');
  return cleanUrl;
};

export const API_BASE_URL = resolveBaseUrl();

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor:
// 1. Normalizes baseURL and request path to guarantee consistent /api prefix
//    (prevents /api/api/... duplication or losing /api prefix)
// 2. Attaches Authorization Bearer token from sessionStorage
// 3. Attaches X-Case-Id header for case selection
apiClient.interceptors.request.use((config) => {
  // Normalize baseURL so it does not end with /api or trailing slashes
  if (config.baseURL) {
    config.baseURL = config.baseURL.replace(/\/+$/, '').replace(/\/api$/, '');
  }

  // Normalize request path if it's a relative URL
  if (config.url && !config.url.startsWith('http://') && !config.url.startsWith('https://')) {
    let path = config.url.startsWith('/') ? config.url : `/${config.url}`;
    // Deduplicate any /api/api/...
    if (path.startsWith('/api/api/')) {
      path = path.replace(/^\/api\/api\//, '/api/');
    } else if (!path.startsWith('/api/') && path !== '/api') {
      // Ensure /api prefix is present to match backend route definitions
      path = `/api${path}`;
    }
    config.url = path;
  }

  const token = sessionStorage.getItem('sakshi_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const caseId = sessionStorage.getItem('sakshi_case_id');
  if (caseId) {
    config.headers['X-Case-Id'] = caseId;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const getActiveCaseId = () => sessionStorage.getItem('sakshi_case_id') || 'SP-014';
export const setActiveCaseId = (caseId) => {
  if (caseId) {
    sessionStorage.setItem('sakshi_case_id', caseId);
    window.dispatchEvent(new CustomEvent('sakshi-case-changed', { detail: { caseId } }));
  }
};

export const authState = {
  getToken: () => sessionStorage.getItem('sakshi_token'),
  getUser: () => {
    try {
      const u = sessionStorage.getItem('sakshi_user');
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  },
  setAuth: (token, user) => {
    if (token) sessionStorage.setItem('sakshi_token', token);
    if (user) sessionStorage.setItem('sakshi_user', JSON.stringify(user));
  },
  clearAuth: () => {
    sessionStorage.removeItem('sakshi_token');
    sessionStorage.removeItem('sakshi_user');
  }
};

// ==========================================
// API Services - Mapped to FastAPI Routes
// ==========================================

// 1. Auth Endpoints
export const loginApi = async (email, password, totp_code = null) => {
  const payload = { email, password };
  if (totp_code) payload.totp_code = totp_code;
  const res = await apiClient.post('/api/auth/login', payload);
  return res.data;
};

export const refreshMfaApi = async (email) => {
  const res = await apiClient.post('/api/auth/mfa-refresh', { email });
  return res.data;
};

export const demoLoginApi = async (name, email, role, website = '') => {
  const res = await apiClient.post('/api/auth/demo-login', { name, email, role, website });
  return res.data;
};

// 2. Summary & Cases
export const getPublicSummaryApi = async () => {
  const res = await apiClient.get('/api/public/summary');
  return res.data;
};

export const getSummaryApi = async () => {
  const res = await apiClient.get('/api/summary');
  return res.data;
};

export const getCaseApi = async () => {
  const res = await apiClient.get('/api/case');
  return res.data;
};

export const getCasesApi = async () => {
  const res = await apiClient.get('/api/cases');
  return res.data;
};

// 3. Cross-Case Analysis
export const getCrossCaseLinksApi = async () => {
  const res = await apiClient.get('/api/cross-case/links');
  return res.data;
};

export const decideCrossCaseLinkApi = async (id, decision) => {
  const res = await apiClient.post(`/api/cross-case/links/${encodeURIComponent(id)}/decision`, { decision });
  return res.data;
};

// 4. Graph & Entities
export const getGraphApi = async (until = null) => {
  const url = until ? `/api/graph?until=${encodeURIComponent(until)}` : '/api/graph';
  const res = await apiClient.get(url);
  return res.data;
};

export const getEntityApi = async (id) => {
  const res = await apiClient.get(`/api/entity/${encodeURIComponent(id)}`);
  return res.data;
};

export const unmaskEntityApi = async (id) => {
  const res = await apiClient.post(`/api/entity/${encodeURIComponent(id)}/unmask`);
  return res.data;
};

export const explainEdgeApi = async (source, target) => {
  const res = await apiClient.get(`/api/edge/${encodeURIComponent(source)}/${encodeURIComponent(target)}/explain`);
  return res.data;
};

// 5. Merge Queue & Entity Resolution
export const getMergeQueueApi = async () => {
  const res = await apiClient.get('/api/merge-queue');
  return res.data;
};

export const approveMergeApi = async (id) => {
  const res = await apiClient.post(`/api/merge/${encodeURIComponent(id)}/approve`);
  return res.data;
};

export const rejectMergeApi = async (id) => {
  const res = await apiClient.post(`/api/merge/${encodeURIComponent(id)}/reject`);
  return res.data;
};

export const unmergeDecisionApi = async (id) => {
  const res = await apiClient.post(`/api/merge/${encodeURIComponent(id)}/unmerge`);
  return res.data;
};
export const unmergeMergeApi = unmergeDecisionApi;

// 6. Alerts & Golden Hour
export const getAlertsApi = async () => {
  const res = await apiClient.get('/api/alerts');
  return res.data;
};

export const getGoldenHourApi = async () => {
  const res = await apiClient.get('/api/golden-hour');
  return res.data;
};

export const simulateRemoveNodeApi = async (nodeId) => {
  const res = await apiClient.post('/api/simulate/remove-node', { node_id: nodeId });
  return res.data;
};

export const getTimelineRangeApi = async () => {
  const res = await apiClient.get('/api/timeline-range');
  return res.data;
};

// 7. Copilot
export const copilotHealthApi = async () => {
  const res = await apiClient.get('/api/health/copilot');
  return res.data;
};

export const askCopilotApi = async (question) => {
  const res = await apiClient.post('/api/copilot', { question });
  return res.data;
};

// 8. Reports
export const generateReportApi = async () => {
  const res = await apiClient.post('/api/report');
  return res.data;
};

export const downloadReportApi = async (reportId = 'RPT-SP014-01') => {
  const res = await apiClient.get(`/api/report/${encodeURIComponent(reportId)}/download`, {
    responseType: 'blob',
  });
  return res.data;
};

export const getReportDownloadUrl = (reportId = 'RPT-SP014-01') => {
  const base = resolveBaseUrl();
  return `${base}/api/report/${encodeURIComponent(reportId)}/download`;
};

export const emailReportApi = async (reportId) => {
  const res = await apiClient.post('/api/report/email', { report_id: reportId });
  return res.data;
};

// Response Interceptor for RBAC
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 403) {
      const detail = error.response.data?.detail || 'Access Denied: Action not permitted for your current role.';
      window.dispatchEvent(new CustomEvent('sakshi-rbac-denied', { detail }));
    }
    return Promise.reject(error);
  }
);

// 9. Ledger & Verification
export const getLedgerApi = async () => {
  const res = await apiClient.get('/api/ledger');
  return res.data;
};

export const verifyLedgerApi = async () => {
  const res = await apiClient.get('/api/verify');
  return res.data;
};

// 10. Debug & Testing
export const debugTamperApi = async () => {
  const res = await apiClient.post('/api/debug/tamper');
  return res.data;
};

export const debugResetTamperApi = async () => {
  const res = await apiClient.post('/api/debug/reset-tamper');
  return res.data;
};

export const debugResetApi = async () => {
  const res = await apiClient.post('/api/debug/reset');
  return res.data;
};

export const simulateInsiderApi = async (userEmail = 'constable@demo.in') => {
  const res = await apiClient.post('/api/debug/simulate-insider', { user_email: userEmail });
  return res.data;
};

// 11. Validation & System Health
export const getValidationApi = async () => {
  const res = await apiClient.get('/api/validation');
  return res.data;
};

export const reloadCaseApi = async () => {
  const res = await apiClient.post('/api/case/reload');
  return res.data;
};

export const healthCheckApi = async () => {
  const res = await apiClient.get('/api/health');
  return res.data;
};

export default apiClient;
