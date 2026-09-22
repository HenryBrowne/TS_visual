import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import JobProgress from "../components/JobProgress.jsx";
import "./ImportWizard.css";

const STEPS = ["Upload", "Map columns", "Preview & validate", "Name & confirm"];
const ROLE_OPTIONS = [
  { value: "timestamp", label: "Timestamp" },
  { value: "series_id", label: "Series ID" },
  { value: "value", label: "Value" },
  { value: "exogenous", label: "Exogenous feature" },
  { value: "ignore", label: "Ignore" },
];

function defaultNameFromFilename(filename) {
  return filename.replace(/\.[^/.]+$/, "");
}

export default function ImportWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [error, setError] = useState(null);

  const [file, setFile] = useState(null);
  const [detecting, setDetecting] = useState(false);
  const [uploadId, setUploadId] = useState(null);
  const [format, setFormat] = useState(null);
  const [columnMapping, setColumnMapping] = useState({});
  const [wideMeltPreview, setWideMeltPreview] = useState(null);
  const [rowCountSampled, setRowCountSampled] = useState(0);

  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState(null);

  const [datasetName, setDatasetName] = useState("");
  const [jobId, setJobId] = useState(null);

  const handleFileSelect = async (selected) => {
    if (!selected) return;
    setFile(selected);
    setError(null);
    setDetecting(true);
    try {
      const result = await api.detectImport(selected);
      setUploadId(result.upload_id);
      setFormat(result.format);
      setColumnMapping(result.column_mapping);
      setWideMeltPreview(result.wide_melt_preview);
      setRowCountSampled(result.row_count_sampled);
      setDatasetName(defaultNameFromFilename(selected.name));
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setDetecting(false);
    }
  };

  const runValidation = async () => {
    setValidating(true);
    setError(null);
    try {
      const result = await api.validateImport({ upload_id: uploadId, format, column_mapping: columnMapping });
      setValidation(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setValidating(false);
    }
  };

  useEffect(() => {
    if (step === 3) runValidation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  const updateRole = (column, role) => {
    setColumnMapping((prev) => ({ ...prev, [column]: role }));
  };

  const wideValueColumns = Object.entries(columnMapping).filter(([, role]) => role === "value");

  const startImport = async () => {
    setError(null);
    try {
      const job = await api.startIngestJob({
        upload_id: uploadId,
        format,
        column_mapping: columnMapping,
        name: datasetName,
      });
      setJobId(job.id);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="import-wizard">
      <h1 className="page-title">Import a dataset</h1>

      <ol className="wizard-steps">
        {STEPS.map((label, i) => (
          <li key={label} className={i + 1 === step ? "active" : i + 1 < step ? "done" : ""}>
            {label}
          </li>
        ))}
      </ol>

      {error && <div className="error-banner">{error}</div>}

      {step === 1 && (
        <div className="card wizard-step">
          <p className="muted">Upload a CSV of your time series data.</p>
          <input
            type="file"
            accept=".csv"
            disabled={detecting}
            onChange={(e) => handleFileSelect(e.target.files?.[0])}
          />
          {detecting && <div className="muted">Detecting format...</div>}
        </div>
      )}

      {step === 2 && (
        <div className="card wizard-step">
          <p className="muted">
            Detected <strong>{format}</strong> format from {rowCountSampled} sampled rows. Adjust any column's
            role below.
          </p>

          <table className="mapping-table">
            <thead>
              <tr>
                <th>Column</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(columnMapping).map(([column, role]) => (
                <tr key={column}>
                  <td className="mapping-column-name">{column}</td>
                  <td>
                    <select value={role} onChange={(e) => updateRole(column, e.target.value)}>
                      {ROLE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {format === "wide" && (
            <div className="wide-melt-notice">
              <strong>{wideValueColumns.length}</strong> column(s) marked "Value" will each become their own
              series: {wideValueColumns.map(([c]) => c).join(", ")}
            </div>
          )}

          <div className="wizard-actions">
            <button className="secondary-button" onClick={() => setStep(1)}>
              Back
            </button>
            <button className="primary-button" onClick={() => setStep(3)}>
              Next
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="card wizard-step">
          {validating && <div className="muted">Validating...</div>}

          {validation && (
            <>
              <div className="validation-summary">
                <span>{validation.row_count} rows sampled</span>
                <span>{validation.valid_row_count} valid</span>
                <span>{validation.series_count} series</span>
                {validation.detected_frequency && <span>frequency: {validation.detected_frequency}</span>}
              </div>

              {validation.errors.map((e, i) => (
                <div key={i} className="chip chip-error">
                  {e}
                </div>
              ))}
              {validation.warnings.map((w, i) => (
                <div key={i} className="chip chip-warning">
                  {w}
                </div>
              ))}

              <table className="mapping-table preview-table">
                <thead>
                  <tr>
                    <th>series_id</th>
                    <th>timestamp</th>
                    <th>value</th>
                  </tr>
                </thead>
                <tbody>
                  {validation.preview_rows.map((row, i) => (
                    <tr key={i}>
                      <td>{String(row.series_id)}</td>
                      <td>{String(row.timestamp)}</td>
                      <td>{String(row.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          <div className="wizard-actions">
            <button className="secondary-button" onClick={() => setStep(2)}>
              Back
            </button>
            <button className="primary-button" disabled={!validation?.can_proceed} onClick={() => setStep(4)}>
              Next
            </button>
          </div>
        </div>
      )}

      {step === 4 && (
        <div className="card wizard-step">
          <label className="dataset-name-label">
            Dataset name
            <input
              type="text"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              disabled={jobId !== null}
            />
          </label>

          {validation && (
            <p className="muted">
              Importing {validation.series_count} series ({validation.valid_row_count} rows sampled valid). This
              will parse the full file, run the profiling battery, and generate LLM diagnostics for every series.
            </p>
          )}

          {!jobId && (
            <div className="wizard-actions">
              <button className="secondary-button" onClick={() => setStep(3)}>
                Back
              </button>
              <button className="primary-button" disabled={!datasetName.trim()} onClick={startImport}>
                Start import
              </button>
            </div>
          )}

          {jobId && (
            <JobProgress
              jobId={jobId}
              label="Ingesting and profiling"
              onSucceeded={() => navigate("/explorer")}
            />
          )}
        </div>
      )}
    </div>
  );
}
