import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import Dashboard from "./Dashboard.jsx";

// The blocker screen's "browse the M4/M5 reference dataset" escape hatch
// must show the reference dataset specifically, not whatever the server's
// default (most-recently-created ready dataset) happens to resolve to --
// that default could just as easily be a newer user upload.
export default function Demo() {
  const [datasetId, setDatasetId] = useState(undefined);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .listDatasets("reference")
      .then((datasets) => {
        if (datasets.length > 0) setDatasetId(datasets[0].id);
        else setError("No reference dataset has been seeded yet.");
      })
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (datasetId === undefined) return <div className="muted">Loading...</div>;

  return <Dashboard datasetId={datasetId} />;
}
