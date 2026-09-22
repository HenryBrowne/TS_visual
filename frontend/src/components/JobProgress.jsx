import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";

const POLL_INTERVAL_MS = 2000;

export default function JobProgress({ jobId, label, onSucceeded, onFailed }) {
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const updated = await api.getJob(jobId);
        if (cancelled) return;
        setJob(updated);
        if (updated.status === "succeeded") {
          clearInterval(pollRef.current);
          onSucceeded?.(updated);
        } else if (updated.status === "failed") {
          clearInterval(pollRef.current);
          onFailed?.(updated);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  if (error) return <div className="error-banner">{error}</div>;
  if (!job) return <div className="muted">Loading job status...</div>;

  const active = job.status === "pending" || job.status === "running";

  return (
    <div className="card job-status">
      <div className="job-status-row">
        {label && <span className="muted">{label}</span>}
        <span className={`badge ${job.status === "succeeded" ? "on" : ""}`}>{job.status}</span>
      </div>
      {active && (
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${job.progress_pct}%` }} />
        </div>
      )}
      {job.status === "running" && <div className="muted">{job.progress_pct.toFixed(1)}% complete</div>}
      {job.status === "failed" && <div className="error-banner">{job.error}</div>}
    </div>
  );
}
