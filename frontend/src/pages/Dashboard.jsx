import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client.js";
import JobProgress from "../components/JobProgress.jsx";
import "./Dashboard.css";

export default function Dashboard({ datasetId } = {}) {
  const [leaderboard, setLeaderboard] = useState(null);
  const [error, setError] = useState(null);
  const [jobId, setJobId] = useState(null);

  const loadLeaderboard = useCallback(async () => {
    try {
      const rows = await api.getLeaderboard(datasetId);
      setLeaderboard(rows);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, [datasetId]);

  useEffect(() => {
    loadLeaderboard();
  }, [loadLeaderboard]);

  const startBenchmark = async () => {
    try {
      const job = await api.startBenchmarkJob(datasetId);
      setJobId(job.id);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Leaderboard</h1>
        <button className="primary-button" onClick={startBenchmark} disabled={jobId !== null}>
          {jobId !== null ? "Benchmark running..." : "Run full benchmark"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {jobId && (
        <JobProgress
          jobId={jobId}
          label="Batch benchmark"
          onSucceeded={() => {
            setJobId(null);
            loadLeaderboard();
          }}
          onFailed={() => setJobId(null)}
        />
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
