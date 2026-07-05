const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

async function req(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

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
