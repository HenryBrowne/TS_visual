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

export const api = {
  listSeries: () => request("/series"),
  getProfile: (id) => request(`/series/${id}/profile`),
  getConfig: (id) => request(`/series/${id}/config`),
  getFeatures: (id) => request(`/series/${id}/features`),
  refit: (id, featureConfig) =>
    request(`/series/${id}/refit`, {
      method: "POST",
      body: JSON.stringify(featureConfig),
    }),
  getLeaderboard: () => request("/leaderboard"),
  startBenchmarkJob: () => request("/jobs/benchmark", { method: "POST" }),
  getJob: (id) => request(`/jobs/${id}`),
};
