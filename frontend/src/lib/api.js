const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ---- access token store ----
let accessToken = localStorage.getItem("assistify_token") || sessionStorage.getItem("assistify_token") || null;

export function setAccessToken(token, remember = true) {
  accessToken = token;
  if (token) {
    (remember ? localStorage : sessionStorage).setItem("assistify_token", token);
    (remember ? sessionStorage : localStorage).removeItem("assistify_token");
  } else {
    localStorage.removeItem("assistify_token");
    sessionStorage.removeItem("assistify_token");
  }
}
export function getAccessToken() {
  return accessToken;
}

export function formatApiErrorDetail(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

let refreshing = null;
async function tryRefresh() {
  if (!refreshing) {
    refreshing = fetch(`${API}/auth/refresh`, { method: "POST", credentials: "include" })
      .then(async (r) => {
        if (!r.ok) throw new Error("refresh failed");
        const data = await r.json();
        setAccessToken(data.accessToken, true);
        return data.accessToken;
      })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

async function rawReq(path, options, token) {
  return fetch(`${API}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
}

async function req(path, options = {}) {
  let res = await rawReq(path, options, accessToken);
  if (res.status === 401 && !path.startsWith("/auth/")) {
    try {
      const newToken = await tryRefresh();
      res = await rawReq(path, options, newToken);
    } catch {
      setAccessToken(null);
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
      throw new Error("Session expired");
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(formatApiErrorDetail(err.detail) || "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

export const authApi = {
  register: (data) => req("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  login: (data) => req("/auth/login", { method: "POST", body: JSON.stringify(data) }),
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
  remove: (id) => req(`/documents/${id}`, { method: "DELETE" }),
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
  search: (q) => req(`/dashboard/search?q=${encodeURIComponent(q)}`),
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
