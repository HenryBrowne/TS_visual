const API_BASE = "http://localhost:8000/api";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${path} failed (${res.status}): ${text}`);
  }
  return res.json();
}

async function requestFile(path, file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", body: formData });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${path} failed (${res.status}): ${text}`);
  }
  return res.json();
}

export const api = {
  listSeries: (datasetId) => request(`/series${datasetId ? `?dataset_id=${datasetId}` : ""}`),
  getProfile: (id, datasetId) => request(`/series/${id}/profile${datasetId ? `?dataset_id=${datasetId}` : ""}`),
  getConfig: (id, datasetId) => request(`/series/${id}/config${datasetId ? `?dataset_id=${datasetId}` : ""}`),
  getFeatures: (id, datasetId) => request(`/series/${id}/features${datasetId ? `?dataset_id=${datasetId}` : ""}`),
  refit: (id, featureConfig, datasetId) =>
    request(`/series/${id}/refit${datasetId ? `?dataset_id=${datasetId}` : ""}`, {
      method: "POST",
      body: JSON.stringify(featureConfig),
    }),
  getLeaderboard: (datasetId) => request(`/leaderboard${datasetId ? `?dataset_id=${datasetId}` : ""}`),
  startBenchmarkJob: (datasetId) =>
    request(`/jobs/benchmark${datasetId ? `?dataset_id=${datasetId}` : ""}`, { method: "POST" }),
  getJob: (id) => request(`/jobs/${id}`),

  listDatasets: (sourceType) => request(`/datasets${sourceType ? `?source_type=${sourceType}` : ""}`),

  detectImport: (file) => requestFile("/import/detect", file),
  validateImport: (payload) =>
    request("/import/validate", { method: "POST", body: JSON.stringify(payload) }),
  startIngestJob: (payload) =>
    request("/jobs/ingest-and-profile", { method: "POST", body: JSON.stringify(payload) }),
};
