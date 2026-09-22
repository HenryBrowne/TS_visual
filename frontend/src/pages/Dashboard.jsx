import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import "./Dashboard.css";

const POLL_INTERVAL_MS = 2000;

function formatPct(n) {
  return `${n.toFixed(2)}%`;
}

export default function Dashboard() {
  const [leaderboard, setLeaderboard] = useState(null);
  const [error, setError] = useState(null);
  const [job, setJob] = useState(null);
  const pollRef = useRef(null);

  const loadLeaderboard = useCallback(async () => {
    try {
      const rows = await api.getLeaderboard();
      setLeaderboard(rows);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    loadLeaderboard();
    return () => clearInterval(pollRef.current);
  }, [loadLeaderboard]);

  const startBenchmark = async () => {
    try {
      const created = await api.startBenchmarkJob();
      setJob(created);
      pollRef.current = setInterval(async () => {
        const updated = await api.getJob(created.id);
        setJob(updated);
        if (updated.status === "succeeded" || updated.status === "failed") {
          clearInterval(pollRef.current);
          if (updated.status === "succeeded") loadLeaderboard();
        }
      }, POLL_INTERVAL_MS);
    } catch (err) {
      setError(err.message);
    }
  };

  const jobRunning = job && (job.status === "pending" || job.status === "running");

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Leaderboard</h1>
        <button className="primary-button" onClick={startBenchmark} disabled={jobRunning}>
          {jobRunning ? "Benchmark running..." : "Run full benchmark"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {job && (
        <div className="card job-status">
          <div className="job-status-row">
            <span className="muted">Job {job.id.slice(0, 8)}</span>
            <span className={`badge ${job.status === "succeeded" ? "on" : ""}`}>{job.status}</span>
          </div>
          {jobRunning && (
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${job.progress_pct}%` }} />
            </div>
          )}
          {job.status === "running" && <div className="muted">{formatPct(job.progress_pct)} complete</div>}
          {job.status === "failed" && <div className="error-banner">{job.error}</div>}
        </div>
      )}

      {leaderboard === null && !error && <div className="muted">Loading leaderboard...</div>}

      {leaderboard !== null && leaderboard.length === 0 && (
        <div className="card empty-state">
          No benchmark results yet. Run the full benchmark to populate the leaderboard.
        </div>
      )}

      {leaderboard !== null && leaderboard.length > 0 && (
        <table className="card leaderboard-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Model</th>
              <th>Avg sMAPE</th>
              <th>Avg MAE</th>
              <th>Avg RMSE</th>
              <th>Series</th>
            </tr>
          </thead>
          <tbody>
            {leaderboard.map((row, i) => (
              <tr key={row.model_name} className={i === 0 ? "best-row" : ""}>
                <td>{i + 1}</td>
                <td className="model-name">{row.model_name}</td>
                <td>{row.avg_smape.toFixed(3)}%</td>
                <td>{row.avg_mae.toFixed(2)}</td>
                <td>{row.avg_rmse.toFixed(2)}</td>
                <td>{row.n_series}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
