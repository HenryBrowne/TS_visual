import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import SeriesChart from "../components/SeriesChart.jsx";
import SeriesCard from "../components/SeriesCard.jsx";
import "./Workbench.css";

const MAX_SELECTED = 5;
const SERIES_COLORS = ["#2f6fed", "#d13c3c", "#1a8f5e", "#b8860b", "#8e44ad"];

export default function Workbench() {
  const [allSeries, setAllSeries] = useState(null);
  const [error, setError] = useState(null);
  const [sidebarSearch, setSidebarSearch] = useState("");
  const [selected, setSelected] = useState([]);
  const [openIds, setOpenIds] = useState(() => new Set());
  const [seriesState, setSeriesState] = useState({});

  useEffect(() => {
    api
      .listSeries()
      .then(setAllSeries)
      .catch((err) => setError(err.message));
  }, []);

  const loadSeries = async (seriesId) => {
    setSeriesState((prev) => ({
      ...prev,
      [seriesId]: { loading: true, error: null },
    }));
    try {
      const features = await api.getFeatures(seriesId);
      const toggleState = Object.fromEntries(features.catalog.map((s) => [s.name, s.enabled]));
      const refit = await api.refit(seriesId, toggleState);

      setSeriesState((prev) => ({
        ...prev,
        [seriesId]: {
          loading: false,
          error: null,
          catalog: features.catalog,
          narrative: features.narrative,
          llmFeatures: features.llm_suggested_features,
          llmModels: features.llm_suggested_models,
          toggleState,
          refit,
          refitLoading: false,
        },
      }));
    } catch (err) {
      setSeriesState((prev) => ({
        ...prev,
        [seriesId]: { loading: false, error: err.message },
      }));
    }
  };

  const addSeries = (seriesId) => {
    if (selected.includes(seriesId) || selected.length >= MAX_SELECTED) return;
    setSelected((prev) => [...prev, seriesId]);
    setOpenIds((prev) => new Set(prev).add(seriesId));
    loadSeries(seriesId);
  };

  const removeSeries = (seriesId) => {
    setSelected((prev) => prev.filter((id) => id !== seriesId));
    setSeriesState((prev) => {
      const next = { ...prev };
      delete next[seriesId];
      return next;
    });
  };

  const toggleOpen = (seriesId) => {
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(seriesId)) next.delete(seriesId);
      else next.add(seriesId);
      return next;
    });
  };

  const toggleFeature = async (seriesId, featureName) => {
    const current = seriesState[seriesId];
    if (!current || current.refitLoading) return;

    const updatedToggleState = { ...current.toggleState, [featureName]: !current.toggleState[featureName] };
    const updatedCatalog = current.catalog.map((s) =>
      s.name === featureName ? { ...s, enabled: !s.enabled } : s,
    );

    setSeriesState((prev) => ({
      ...prev,
      [seriesId]: { ...current, catalog: updatedCatalog, toggleState: updatedToggleState, refitLoading: true },
    }));

    try {
      const refit = await api.refit(seriesId, updatedToggleState);
      setSeriesState((prev) => ({
        ...prev,
        [seriesId]: { ...prev[seriesId], refit, refitLoading: false },
      }));
    } catch (err) {
      setSeriesState((prev) => ({
        ...prev,
        [seriesId]: { ...prev[seriesId], error: err.message, refitLoading: false },
      }));
    }
  };

  const filteredSidebar =
    allSeries?.filter((s) => s.series_id.toLowerCase().includes(sidebarSearch.toLowerCase())) ?? [];

  const chartEntries = selected
    .map((id, i) => {
      const state = seriesState[id];
      if (!state?.refit) return null;
      const bestModel = state.refit.best_model;
      return {
        id,
        color: SERIES_COLORS[i % SERIES_COLORS.length],
        actual: state.refit.actual,
        forecast: state.refit.forecast[bestModel],
        forecastLabel: bestModel,
      };
    })
    .filter(Boolean);

  return (
    <div className="workbench">
      <aside className="workbench-sidebar card">
        <input
          className="search-input"
          type="text"
          placeholder="Search series..."
          value={sidebarSearch}
          onChange={(e) => setSidebarSearch(e.target.value)}
        />
        <div className="muted sidebar-hint">
          {selected.length}/{MAX_SELECTED} selected
        </div>
        <div className="sidebar-list">
          {filteredSidebar.map((s) => {
            const isSelected = selected.includes(s.series_id);
            const atCap = !isSelected && selected.length >= MAX_SELECTED;
            return (
              <button
                key={s.series_id}
                className={`sidebar-item ${isSelected ? "selected" : ""}`}
                disabled={atCap}
                onClick={() => (isSelected ? removeSeries(s.series_id) : addSeries(s.series_id))}
              >
                <span>{s.series_id}</span>
                <span className="muted">{s.frequency}</span>
              </button>
            );
          })}
        </div>
      </aside>

      <div className="workbench-main">
        <h1 className="page-title">Workbench</h1>
        {error && <div className="error-banner">{error}</div>}

        {selected.length === 0 && (
          <div className="card empty-state">Select up to {MAX_SELECTED} series from the sidebar to compare.</div>
        )}

        {chartEntries.length > 0 && (
          <div className="card chart-card">
            <SeriesChart entries={chartEntries} />
          </div>
        )}

        <div className="series-cards">
          {selected.map((id, i) => (
            <SeriesCard
              key={id}
              seriesId={id}
              color={SERIES_COLORS[i % SERIES_COLORS.length]}
              state={seriesState[id] ?? { loading: true }}
              open={openIds.has(id)}
              onToggleOpen={toggleOpen}
              onToggleFeature={toggleFeature}
              onRemove={removeSeries}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
