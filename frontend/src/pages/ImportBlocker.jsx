import { Link } from "react-router-dom";
import "./ImportBlocker.css";

export default function ImportBlocker() {
  return (
    <div className="import-blocker">
      <div className="card import-blocker-card">
        <h1 className="page-title">Import your own data to get started</h1>
        <p className="muted">
          Upload a CSV of your own time series and this app will profile it, suggest features, and
          benchmark forecasting models against it.
        </p>
        <Link to="/import" className="primary-button import-blocker-cta">
          Import a dataset
        </Link>
        <div className="import-blocker-secondary">
          or <Link to="/demo">browse the M4/M5 reference dataset</Link> instead
        </div>
      </div>
    </div>
  );
}
