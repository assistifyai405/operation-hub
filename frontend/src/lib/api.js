const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/** Readable CSRF cookie set by the API (not httpOnly). */
export function getCsrfToken() {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

/** Clear any legacy JWT keys left from older builds. */
export function clearLegacyTokenStorage() {
  try {
    localStorage.removeItem("assistify_token");
    sessionStorage.removeItem("assistify_token");
  } catch {
    /* ignore */
  }
}

/** @deprecated Cookie-only auth — always null. Kept so accidental imports do not break. */
export function getAccessToken() {
  return null;
}

/** @deprecated No-op — tokens are httpOnly cookies. */
export function setAccessToken() {
  clearLegacyTokenStorage();
}

export function formatApiErrorDetail(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail === "object") {
    // Sprint 18 envelope: { error: { code, message, requestId } }
    if (detail.error && typeof detail.error === "object") {
      const e = detail.error;
      if (e.actionable && e.message) return `${e.message} — ${e.actionable}`;
      if (typeof e.message === "string") return e.message;
    }
    if (detail.actionable && detail.message) return `${detail.message} — ${detail.actionable}`;
    if (typeof detail.message === "string") return detail.message;
    if (typeof detail.msg === "string") return detail.msg;
    // readiness body embedded in detail
    if (detail.status === "degraded" && detail.checks) return "Service not ready";
  }
  return String(detail);
}

let refreshing = null;
async function tryRefresh() {
  if (!refreshing) {
    refreshing = fetch(`${API}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    })
      .then(async (r) => {
        if (!r.ok) throw new Error("refresh failed");
        await r.json().catch(() => ({}));
        return true;
      })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

function csrfHeaders(method, extra = {}) {
  const headers = { ...extra };
  const upper = (method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(upper)) {
    const csrf = getCsrfToken();
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  return headers;
}

async function rawReq(path, options = {}) {
  const method = options.method || "GET";
  const headers = csrfHeaders(method, {
    ...(options.body !== undefined && !(options.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : {}),
    ...(options.headers || {}),
  });
  return fetch(`${API}${path}`, {
    credentials: "include",
    ...options,
    headers,
  });
}

async function req(path, options = {}) {
  let res = await rawReq(path, options);
  if (res.status === 401 && !path.startsWith("/auth/")) {
    try {
      await tryRefresh();
      res = await rawReq(path, options);
    } catch {
      clearLegacyTokenStorage();
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
      throw new Error("Session expired");
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(formatApiErrorDetail(err.detail || err.error || err) || "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

/** Cookie-session restore (no localStorage). */
export async function bootstrapSession() {
  try {
    const res = await fetch(`${API}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!res.ok) return null;
    const data = await res.json().catch(() => ({}));
    return data.user || null;
  } catch {
    return null;
  }
}

/** Generic JSON helper used by AuthContext and ad-hoc callers. */
export async function api(path, { method = "GET", body, headers = {}, skipAuth = false } = {}) {
  const opts = { method, headers: { ...headers } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  let res = await rawReq(path, opts);
  if (res.status === 401 && !skipAuth && !path.startsWith("/auth/")) {
    try {
      await tryRefresh();
      res = await rawReq(path, opts);
    } catch {
      clearLegacyTokenStorage();
      throw new Error("Session expired");
    }
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(formatApiErrorDetail(data.detail || data.error || data) || "Request failed");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export async function apiUpload(path, formData) {
  let res = await rawReq(path, { method: "POST", body: formData, headers: {} });
  if (res.status === 401) {
    await tryRefresh();
    res = await rawReq(path, { method: "POST", body: formData, headers: {} });
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(formatApiErrorDetail(data.detail) || "Upload failed");
    err.status = res.status;
    throw err;
  }
  return data;
}

export const authApi = {
  register: (data) => req("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  login: (data) => req("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  demo: () => req("/auth/demo", { method: "POST" }),
  logout: () => req("/auth/logout", { method: "POST" }),
  me: () => req("/auth/me"),
  refresh: () => req("/auth/refresh", { method: "POST" }),
  forgotPassword: (email) => req("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) }),
  resetPassword: (token, password) => req("/auth/reset-password", { method: "POST", body: JSON.stringify({ token, password }) }),
  verifyEmail: (token) => req("/auth/verify-email", { method: "POST", body: JSON.stringify({ token }) }),
  resendVerification: () => req("/auth/resend-verification", { method: "POST" }),
  updateProfile: (data) => req("/auth/profile", { method: "PATCH", body: JSON.stringify(data) }),
  changePassword: (data) => req("/auth/change-password", { method: "POST", body: JSON.stringify(data) }),
  organization: () => req("/auth/organization"),
  sessions: () => req("/auth/sessions"),
  revokeSession: (id) => req(`/auth/sessions/${id}`, { method: "DELETE" }),
};

export const clientsApi = {
  list: () => req("/clients"),
  create: (data) => req("/clients", { method: "POST", body: JSON.stringify(data) }),
  update: (id, data) => req(`/clients/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  remove: (id) => req(`/clients/${id}`, { method: "DELETE" }),
};

export const projectsApi = {
  list: () => req("/projects"),
  get: (id) => req(`/projects/${id}`),
  create: (data) => req("/projects", { method: "POST", body: JSON.stringify(data) }),
  update: (id, data) => req(`/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  remove: (id) => req(`/projects/${id}`, { method: "DELETE" }),
};

export const tasksApi = {
  list: (projectId) => req(`/tasks${projectId ? `?project_id=${projectId}` : ""}`),
  create: (data) => req("/tasks", { method: "POST", body: JSON.stringify(data) }),
  update: (id, data) => req(`/tasks/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  remove: (id) => req(`/tasks/${id}`, { method: "DELETE" }),
};

export const documentsApi = {
  list: (projectId) => req(`/documents${projectId ? `?project_id=${projectId}` : ""}`),
  create: (data) => req("/documents", { method: "POST", body: JSON.stringify(data) }),
  rename: (id, name) => req(`/documents/${id}`, { method: "PUT", body: JSON.stringify({ name }) }),
  remove: (id) => req(`/documents/${id}`, { method: "DELETE" }),
  upload: async (file, projectId) => {
    const fd = new FormData();
    fd.append("file", file);
    if (projectId) fd.append("project_id", projectId);
    return apiUpload("/documents/upload", fd);
  },
  fileUrl: (id) => `${API}/documents/${id}/file`,
};

export const libraryApi = {
  documents: (params) => req(`/library/documents?${new URLSearchParams(params)}`),
  proposals: (params) => req(`/library/proposals?${new URLSearchParams(params)}`),
  contracts: (params) => req(`/library/contracts?${new URLSearchParams(params)}`),
  invoices: (params) => req(`/library/invoices?${new URLSearchParams(params)}`),
};

export const analyticsApi = { get: () => req("/analytics") };
export const notificationsApi = { list: () => req("/notifications") };

export const aiApi = {
  activities: (scope = "today", limit = 20) => req(`/ai/activities?scope=${scope}&limit=${limit}`),
  history: () => req("/ai/activities/history"),
  timeSaved: () => req("/ai/time-saved"),
  insights: () => req("/ai/insights"),
  notifications: () => req("/ai/notifications"),
  workspaceStats: () => req("/ai/workspace/stats"),
  workspaceSearch: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return req(`/ai/workspace/search${qs ? `?${qs}` : ""}`);
  },
  workspaceVersions: () => req("/ai/workspace/versions"),
};

const API_BASE = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const memoryApi = {
  memories: (params = {}) => { const qs = new URLSearchParams(params).toString(); return req(`/memory/memories${qs ? `?${qs}` : ""}`); },
  stats: () => req("/memory/stats"),
  create: (body) => req("/memory/memories", { method: "POST", body: JSON.stringify(body) }),
  update: (id, body) => req(`/memory/memories/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  remove: (id) => req(`/memory/memories/${id}`, { method: "DELETE" }),
  pin: (id, pinned) => req(`/memory/memories/${id}/pin`, { method: "PATCH", body: JSON.stringify({ pinned }) }),
  toggleLearning: (id, learning_enabled) => req(`/memory/memories/${id}/learning`, { method: "PATCH", body: JSON.stringify({ learning_enabled }) }),
  merge: (body) => req("/memory/memories/merge", { method: "POST", body: JSON.stringify(body) }),
  learnEvent: (body) => req("/memory/learn/event", { method: "POST", body: JSON.stringify(body) }),
  analyze: () => req("/memory/learn/analyze", { method: "POST" }),
  businessProfile: () => req("/memory/business-profile"),
  generateProfile: () => req("/memory/business-profile", { method: "POST" }),
  insights: (refresh = false) => req(`/memory/insights?refresh=${refresh}`),
  search: (q) => req(`/memory/search?q=${encodeURIComponent(q)}`),
  ask: (question) => req("/memory/ask", { method: "POST", body: JSON.stringify({ question }) }),
};

export const crmApi = {
  contacts: () => req("/crm/contacts"),
  contact: (id) => req(`/crm/contacts/${id}`),
  contactSummary: (id, refresh = false) => req(`/crm/contacts/${id}/ai-summary?refresh=${refresh}`, { method: "POST" }),
  leads: () => req("/crm/leads"),
  pipeline: (params = {}) => { const qs = new URLSearchParams(params).toString(); return req(`/crm/pipeline${qs ? `?${qs}` : ""}`); },
  getLead: (id) => req(`/crm/leads/${id}`),
  createLead: (body) => req("/crm/leads", { method: "POST", body: JSON.stringify(body) }),
  updateLead: (id, body) => req(`/crm/leads/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  moveStage: (id, stage) => req(`/crm/leads/${id}/stage`, { method: "PATCH", body: JSON.stringify({ stage }) }),
  deleteLead: (id) => req(`/crm/leads/${id}`, { method: "DELETE" }),
  leadBrief: (id, refresh = false) => req(`/crm/leads/${id}/ai-brief?refresh=${refresh}`, { method: "POST" }),
  convert: (id) => req(`/crm/leads/${id}/convert`, { method: "POST" }),
  search: (q) => req(`/crm/search?q=${encodeURIComponent(q)}`),
  salesMetrics: () => req("/crm/sales-metrics"),
};

export const opportunitiesApi = {
  list: () => req("/opportunities"),
  brief: () => req("/opportunities/brief"),
  health: () => req("/opportunities/health"),
  dismiss: (key) => req("/opportunities/dismiss", { method: "POST", body: JSON.stringify({ key }) }),
  archiveProject: (projectId) => req(`/opportunities/archive-project/${projectId}`, { method: "POST" }),
};

export const automationApi = {
  summary: () => req("/automation/summary"),
  getSettings: () => req("/automation/settings"),
  updateSettings: (body) => req("/automation/settings", { method: "PATCH", body: JSON.stringify(body) }),
  pause: (duration) => req("/automation/pause", { method: "POST", body: JSON.stringify({ duration }) }),
  resume: () => req("/automation/resume", { method: "POST" }),
  automations: () => req("/automation/automations"),
  createAutomation: (body) => req("/automation/automations", { method: "POST", body: JSON.stringify(body) }),
  updateAutomation: (id, body) => req(`/automation/automations/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  toggleAutomation: (id, enabled) => req(`/automation/automations/${id}/toggle`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
  setMode: (id, mode) => req(`/automation/automations/${id}/mode`, { method: "PATCH", body: JSON.stringify({ mode }) }),
  deleteAutomation: (id) => req(`/automation/automations/${id}`, { method: "DELETE" }),
  builderOptions: () => req("/automation/builder-options"),
  approvals: (status = "pending") => req(`/automation/approvals?status=${status}`),
  approve: (id) => req(`/automation/approvals/${id}/approve`, { method: "POST" }),
  reject: (id) => req(`/automation/approvals/${id}/reject`, { method: "POST" }),
  prepareSuggestion: (id) => req(`/automation/approvals/${id}/prepare`, { method: "POST" }),
  editApproval: (id, actions) => req(`/automation/approvals/${id}`, { method: "PUT", body: JSON.stringify({ actions }) }),
  logs: (limit = 100) => req(`/automation/logs?limit=${limit}`),
  run: () => req("/automation/run", { method: "POST" }),
};

export const assistantApi = {
  action: (body) => req("/assistant/action", { method: "POST", body: JSON.stringify(body) }),
  history: (session_id) => req(`/assistant/history/${session_id}`),
  suggestions: (scope = "generic", documentType = "") =>
    req(`/assistant/suggestions?scope=${encodeURIComponent(scope)}&document_type=${encodeURIComponent(documentType || "")}`),
  streamUrl: () => `${API_BASE}/assistant/chat/stream`,
};

export const copilotApi = {
  message: (session_id, message) => req("/copilot/message", { method: "POST", body: JSON.stringify({ session_id, message }) }),
  execute: (session_id, action_id) => req("/copilot/execute", { method: "POST", body: JSON.stringify({ session_id, action_id }) }),
  history: (session_id) => req(`/copilot/history/${session_id}`),
  suggestions: () => req("/copilot/suggestions"),
};

export const settingsApi = {
  get: () => req("/settings"),
  updateOrganization: (data) => req("/settings/organization", { method: "PATCH", body: JSON.stringify(data) }),
  updateBranding: (values) => req("/settings/branding", { method: "PATCH", body: JSON.stringify({ values }) }),
  updateAI: (values) => req("/settings/ai", { method: "PATCH", body: JSON.stringify({ values }) }),
  updateDocuments: (values) => req("/settings/documents", { method: "PATCH", body: JSON.stringify({ values }) }),
  updateEmail: (values) => req("/settings/email", { method: "PATCH", body: JSON.stringify({ values }) }),
  updateNotifications: (values) => req("/settings/notifications", { method: "PATCH", body: JSON.stringify({ values }) }),
  billing: () => req("/settings/billing"),
  apiKeys: () => req("/settings/api-keys"),
  recentLogins: () => req("/settings/recent-logins"),
  logoutAll: () => req("/auth/logout-all", { method: "POST" }),
  imageUrl: (url) => `${process.env.REACT_APP_BACKEND_URL}${url}`,
  uploadImage: async (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiUpload("/settings/upload-image", fd);
  },
};

export const proposalsApi = {
  list: (projectId) => req(`/proposals${projectId ? `?project_id=${projectId}` : ""}`),
  create: (data) => req("/proposals", { method: "POST", body: JSON.stringify(data) }),
  remove: (id) => req(`/proposals/${id}`, { method: "DELETE" }),
};

export const activitiesApi = {
  list: (projectId) => req(`/activities?project_id=${projectId}`),
};

export const dashboardApi = {
  summary: () => req("/dashboard/summary"),
  executive: () => req("/dashboard/executive"),
  morningBrief: () => req("/dashboard/morning-brief"),
  search: (q) => req(`/dashboard/search?q=${encodeURIComponent(q)}`),
};

export const onboardingApi = {
  get: () => req("/onboarding"),
  complete: () => req("/onboarding/complete", { method: "POST" }),
  getState: () => req("/onboarding/state"),
  saveState: (body) => req("/onboarding/state", { method: "POST", body: JSON.stringify(body) }),
  restart: () => req("/onboarding/restart", { method: "POST" }),
  flag: (key) => req("/onboarding/flag", { method: "POST", body: JSON.stringify({ key }) }),
  analyzeWebsite: (url) => req("/onboarding/analyze-website", { method: "POST", body: JSON.stringify({ url }) }),
  generateProfile: (body) => req("/onboarding/profile", { method: "POST", body: JSON.stringify(body) }),
  updateProfile: (sections) => req("/onboarding/profile", { method: "PUT", body: JSON.stringify({ sections }) }),
  seedDemo: () => req("/onboarding/seed-demo", { method: "POST" }),
  demoStatus: () => req("/onboarding/demo-status"),
  clearDemo: () => req("/onboarding/demo-data", { method: "DELETE" }),
  checklist: () => req("/onboarding/checklist"),
  dismissChecklist: () => req("/onboarding/checklist/dismiss", { method: "POST" }),
};

export const plansApi = {
  generate: (projectId) => req(`/projects/${projectId}/plan/generate`, { method: "POST" }),
  list: (projectId) => req(`/projects/${projectId}/plans`),
  save: (projectId, sections) => req(`/projects/${projectId}/plans`, { method: "POST", body: JSON.stringify({ sections }) }),
};

export const proposalWriterApi = {
  sections: () => req("/proposal/sections"),
  generate: (projectId) => req(`/projects/${projectId}/proposal/generate`, { method: "POST" }),
  get: (projectId) => req(`/projects/${projectId}/proposal`),
  save: (projectId, data) => req(`/projects/${projectId}/proposal`, { method: "POST", body: JSON.stringify(data) }),
  versions: (projectId) => req(`/projects/${projectId}/proposal/versions`),
  restore: (projectId, version) => req(`/projects/${projectId}/proposal/restore/${version}`, { method: "POST" }),
  exportUrl: (projectId, fmt) => `${process.env.REACT_APP_BACKEND_URL}/api/projects/${projectId}/proposal/export/${fmt}`,
};

export const contractWriterApi = {
  sections: () => req("/contract/sections"),
  generate: (projectId) => req(`/projects/${projectId}/contract/generate`, { method: "POST" }),
  get: (projectId) => req(`/projects/${projectId}/contract`),
  save: (projectId, data) => req(`/projects/${projectId}/contract`, { method: "POST", body: JSON.stringify(data) }),
  versions: (projectId) => req(`/projects/${projectId}/contract/versions`),
  restore: (projectId, version) => req(`/projects/${projectId}/contract/restore/${version}`, { method: "POST" }),
  exportUrl: (projectId, fmt) => `${process.env.REACT_APP_BACKEND_URL}/api/projects/${projectId}/contract/export/${fmt}`,
};

export const invoiceWriterApi = {
  config: () => req("/invoice/config"),
  generate: (projectId) => req(`/projects/${projectId}/invoice/generate`, { method: "POST" }),
  get: (projectId) => req(`/projects/${projectId}/invoice`),
  save: (projectId, data) => req(`/projects/${projectId}/invoice`, { method: "POST", body: JSON.stringify(data) }),
  versions: (projectId) => req(`/projects/${projectId}/invoice/versions`),
  restore: (projectId, version) => req(`/projects/${projectId}/invoice/restore/${version}`, { method: "POST" }),
  exportUrl: (projectId, fmt) => `${process.env.REACT_APP_BACKEND_URL}/api/projects/${projectId}/invoice/export/${fmt}`,
};

export const teamApi = {
  members: () => req("/team/members"),
  seats: () => req("/team/seats"),
  invitations: () => req("/team/invitations"),
  invite: (body) => req("/team/invitations", { method: "POST", body: JSON.stringify(body) }),
  cancelInvitation: (id) => req(`/team/invitations/${id}`, { method: "DELETE" }),
  previewInvitation: (token) => req(`/team/invitations/preview/${encodeURIComponent(token)}`),
  acceptInvitation: (token) => req(`/team/invitations/${encodeURIComponent(token)}/accept`, { method: "POST" }),
  changeRole: (userId, role) => req(`/team/members/${userId}/role`, { method: "PATCH", body: JSON.stringify({ role }) }),
  removeMember: (userId) => req(`/team/members/${userId}`, { method: "DELETE" }),
  transferOwnership: (userId) => req("/team/transfer-ownership", { method: "POST", body: JSON.stringify({ userId }) }),
};

export const emailsApi = {
  list: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set("status", params.status);
    if (params.q) qs.set("q", params.q);
    const s = qs.toString();
    return req(`/emails${s ? `?${s}` : ""}`);
  },
  status: () => req("/emails/status"),
  get: (id) => req(`/emails/${id}`),
  create: (body) => req("/emails", { method: "POST", body: JSON.stringify(body) }),
  update: (id, body) => req(`/emails/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  submit: (id) => req(`/emails/${id}/submit`, { method: "POST" }),
  approve: (id) => req(`/emails/${id}/approve`, { method: "POST" }),
  reject: (id, reason) => req(`/emails/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  send: (id) => req(`/emails/${id}/send`, { method: "POST" }),
  cancel: (id) => req(`/emails/${id}/cancel`, { method: "POST" }),
  retry: (id) => req(`/emails/${id}/retry`, { method: "POST" }),
  improve: (id, body = {}) => req(`/emails/${id}/improve`, { method: "POST", body: JSON.stringify(body) }),
};

export const integrationsApi = {
  list: () => req("/integrations"),
  status: () => req("/integrations/status"),
  connect: (body) => req("/integrations/connect", { method: "POST", body: JSON.stringify(body) }),
  disconnect: (body) => req("/integrations/disconnect", { method: "POST", body: JSON.stringify(body) }),
  refresh: (body) => req("/integrations/refresh", { method: "POST", body: JSON.stringify(body) }),
  health: (body) => req("/integrations/health", { method: "POST", body: JSON.stringify(body) }),
};

export const inboxApi = {
  mailboxes: () => req("/inbox/mailboxes"),
  ensureMailbox: (provider) => req("/inbox/mailboxes/ensure", { method: "POST", body: JSON.stringify({ provider }) }),
  patchMailbox: (id, body) => req(`/inbox/mailboxes/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  syncMailbox: (id, forceFull = false) => req(`/inbox/mailboxes/${id}/sync?force_full=${forceFull ? "true" : "false"}`, { method: "POST" }),
  threads: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v === undefined || v === null || v === "") return;
      qs.set(k, String(v));
    });
    const s = qs.toString();
    return req(`/inbox/threads${s ? `?${s}` : ""}`);
  },
  getThread: (id) => req(`/inbox/threads/${id}`),
  patchThread: (id, body) => req(`/inbox/threads/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  messages: (id) => req(`/inbox/threads/${id}/messages`),
  summarize: (id) => req(`/inbox/threads/${id}/summarize`, { method: "POST" }),
  draftReply: (id) => req(`/inbox/threads/${id}/draft-reply`, { method: "POST" }),
  link: (id, body) => req(`/inbox/threads/${id}/link`, { method: "POST", body: JSON.stringify(body) }),
  unlink: (id) => req(`/inbox/threads/${id}/link`, { method: "DELETE" }),
};

export const opsApi = {
  status: () => req("/ops/status"),
  retryJob: (id) => req(`/ops/jobs/${id}/retry`, { method: "POST" }),
  syncMailbox: (id) => req(`/ops/mailboxes/${id}/sync`, { method: "POST" }),
  reconcile: () => req("/ops/emails/reconcile", { method: "POST" }),
  resolveEmail: (id, body) => req(`/ops/emails/${id}/resolve`, { method: "POST", body: JSON.stringify(body) }),
  integrationHealth: (provider) => req(`/ops/integrations/${provider}/health`, { method: "POST" }),
};
