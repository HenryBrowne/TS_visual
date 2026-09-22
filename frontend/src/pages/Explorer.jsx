import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import "./Explorer.css";

export default function Explorer() {
  const [series, setSeries] = useState(null);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [frequencyFilter, setFrequencyFilter] = useState("all");
  const [seasonalOnly, setSeasonalOnly] = useState(false);
  const [trendOnly, setTrendOnly] = useState(false);
  const [intermittencyFilter, setIntermittencyFilter] = useState("all");

  useEffect(() => {
    api
      .listSeries()
      .then(setSeries)
      .catch((err) => setError(err.message));
  }, []);

  const frequencies = useMemo(() => {
    if (!series) return [];
    return [...new Set(series.map((s) => s.frequency))].sort();
  }, [series]);

  const intermittencyCategories = useMemo(() => {
    if (!series) return [];
    const cats = series
      .map((s) => s.profile_summary?.intermittency_category)
      .filter(Boolean);
    return [...new Set(cats)].sort();
  }, [series]);

  const filtered = useMemo(() => {
    if (!series) return [];
    return series.filter((s) => {
      if (search && !s.series_id.toLowerCase().includes(search.toLowerCase())) return false;
      if (frequencyFilter !== "all" && s.frequency !== frequencyFilter) return false;
      if (seasonalOnly && !s.profile_summary?.seasonality_detected) return false;
      if (trendOnly && !s.profile_summary?.trend_detected) return false;
      if (
        intermittencyFilter !== "all" &&
        s.profile_summary?.intermittency_category !== intermittencyFilter
      )
        return false;
      return true;
    });
  }, [series, search, frequencyFilter, seasonalOnly, trendOnly, intermittencyFilter]);

  return (
    <div>
      <h1 className="page-title">Series Explorer</h1>

      {error && <div className="error-banner">{error}</div>}

      <div className="card explorer-filters">
        <input
          className="search-input"
          type="text"
          placeholder="Search series ID..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={frequencyFilter} onChange={(e) => setFrequencyFilter(e.target.value)}>
          <option value="all">All frequencies</option>
          {frequencies.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
        <select value={intermittencyFilter} onChange={(e) => setIntermittencyFilter(e.target.value)}>
          <option value="all">All intermittency</option>
          {intermittencyCategories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <label className="filter-checkbox">
          <input type="checkbox" checked={trendOnly} onChange={(e) => setTrendOnly(e.target.checked)} />
          Trend detected
        </label>
        <label className="filter-checkbox">
          <input
            type="checkbox"
            checked={seasonalOnly}
            onChange={(e) => setSeasonalOnly(e.target.checked)}
          />
          Seasonality detected
        </label>
      </div>

      {series === null && !error && <div className="muted">Loading series...</div>}

      {series !== null && (
        <>
          <div className="muted result-count">
            {filtered.length} of {series.length} series
          </div>
          <table className="card explorer-table">
            <thead>
              <tr>
                <th>Series</th>
                <th>Dataset</th>
                <th>Frequency</th>
                <th>Obs</th>
                <th>Trend</th>
                <th>Seasonality</th>
                <th>Stationary</th>
                <th>Intermittency</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => {
                const p = s.profile_summary;
                return (
                  <tr key={s.series_id}>
                    <td className="series-id">{s.series_id}</td>
                    <td>{s.dataset}</td>
                    <td>{s.frequency}</td>
                    <td>{s.n_obs}</td>
                    <td>
                      {p ? (
                        <span className={`badge ${p.trend_detected ? "on" : ""}`}>
                          {p.trend_detected ? "trend" : "none"}
                        </span>
                      ) : (
                        <span className="muted">-</span>
                      )}
                    </td>
                    <td>
                      {p ? (
                        <span className={`badge ${p.seasonality_detected ? "on" : ""}`}>
                          {p.seasonality_detected ? `period ${p.seasonality_period}` : "none"}
                        </span>
                      ) : (
                        <span className="muted">-</span>
                      )}
                    </td>
                    <td>
                      {p ? (
                        <span className={`badge ${p.stationary ? "on" : ""}`}>
                          {p.stationary ? "stationary" : "non-stationary"}
                        </span>
                      ) : (
                        <span className="muted">-</span>
                      )}
                    </td>
                    <td>{p ? <span className="badge">{p.intermittency_category}</span> : <span className="muted">-</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
