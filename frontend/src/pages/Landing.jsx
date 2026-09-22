import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import JobProgress from "../components/JobProgress.jsx";
import Dashboard from "./Dashboard.jsx";
import ImportBlocker from "./ImportBlocker.jsx";

const SEEN_DEMO_KEY = "hasSeenM4Demo";

function hasSeenDemo() {
  try {
    return localStorage.getItem(SEEN_DEMO_KEY) === "true";
  } catch {
    return false; // localStorage unavailable (private mode, etc.) -- treat as not seen
  }
}

function markDemoSeen() {
  try {
    localStorage.setItem(SEEN_DEMO_KEY, "true");
  } catch {
    // ignore -- worst case the demo shows again next visit
  }
}

// Decides what a first-time-at-"/" visitor sees, per this order:
// 1. Any ready user_upload dataset -> normal dashboard (it's already the
//    most-recently-created ready dataset, so no special routing needed).
// 2. A user_upload dataset mid-import -> its job progress view.
// 3. Neither, and the "seen the demo" flag is unset -> M4 reference
//    dashboard, and set the flag (marks "first visit resolved", not
//    "demo was read" -- set immediately, not on some view/scroll event).
// 4. Flag already set -> the import blocker.
export default function Landing() {
  const [decision, setDecision] = useState(null);
  const [processingJobId, setProcessingJobId] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;

    async function decide() {
      try {
        const userUploads = await api.listDatasets("user_upload");
        if (cancelled) return;

        if (userUploads.some((d) => d.status === "ready")) {
          setDecision("dashboard");
          return;
        }

        const processing = userUploads.find((d) => d.status === "processing" && d.job_id);
        if (processing) {
          setProcessingJobId(processing.job_id);
          setDecision("processing");
          return;
        }

        if (!hasSeenDemo()) {
          markDemoSeen();
          setDecision("dashboard");
          return;
        }

        setDecision("blocker");
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    decide();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (decision === null) return <div className="muted">Loading...</div>;
  if (decision === "dashboard") return <Dashboard />;
  if (decision === "blocker") return <ImportBlocker />;

  return (
    <div>
      <h1 className="page-title">Import in progress</h1>
      <JobProgress
        jobId={processingJobId}
        label="Ingesting and profiling your dataset"
        onSucceeded={() => navigate("/explorer")}
      />
    </div>
  );
}
