const FEATURE_TYPE_LABEL = {
  calendar: "Calendar",
  lag: "Lag",
  rolling_stat: "Rolling stat",
  fourier: "Fourier",
  holiday: "Holiday",
};

function DeltaRow({ label, before, after, formatter = (v) => v.toFixed(3) }) {
  const improved = after < before;
  return (
    <div className="delta-row">
      <span className="delta-label">{label}</span>
      <span className="delta-value">{formatter(before)}</span>
      <span className="delta-arrow">→</span>
      <span className={`delta-value ${improved ? "delta-good" : ""}`}>{formatter(after)}</span>
    </div>
  );
}

export default function SeriesCard({ seriesId, color, state, open, onToggleOpen, onToggleFeature, onRemove }) {
  if (state.loading) {
    return (
      <div className="card series-card">
        <div className="series-card-header">
          <span className="series-swatch" style={{ background: color }} />
          <span className="series-card-title">{seriesId}</span>
          <span className="muted">Loading...</span>
        </div>
      </div>
    );
  }

  if (state.error) {
    return (
      <div className="card series-card">
        <div className="series-card-header">
          <span className="series-swatch" style={{ background: color }} />
          <span className="series-card-title">{seriesId}</span>
          <button className="icon-button" onClick={() => onRemove(seriesId)}>
            ✕
          </button>
        </div>
        <div className="error-banner">{state.error}</div>
      </div>
    );
  }

  const { catalog, narrative, llmFeatures, llmModels, refit, refitLoading } = state;
  const bestModel = refit?.best_model;
  const deltas = refit?.deltas;

  return (
    <div className="card series-card">
      <button className="series-card-header" onClick={() => onToggleOpen(seriesId)}>
        <span className="series-swatch" style={{ background: color }} />
        <span className="series-card-title">{seriesId}</span>
        {bestModel && <span className="badge on">{bestModel}</span>}
        {refitLoading && <span className="muted">refitting...</span>}
        <span className="spacer" />
        <span
          className="icon-button"
          role="button"
          tabIndex={-1}
          onClick={(e) => {
            e.stopPropagation();
            onRemove(seriesId);
          }}
        >
          ✕
        </span>
        <span className="chevron">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="series-card-body">
          {narrative && <p className="narrative">{narrative}</p>}

          <div className="series-card-columns">
            <div>
              <h4 className="section-heading">Features</h4>
              <div className="feature-list">
                {catalog.map((spec) => (
                  <label key={spec.name} className="feature-toggle">
                    <input
                      type="checkbox"
                      checked={spec.enabled}
                      onChange={() => onToggleFeature(seriesId, spec.name)}
                    />
                    <span className="feature-name">{spec.name}</span>
                    <span className="badge">{FEATURE_TYPE_LABEL[spec.feature_type]}</span>
                  </label>
                ))}
              </div>

              {llmFeatures?.length > 0 && (
                <>
                  <h4 className="section-heading">LLM diagnostic notes</h4>
                  <ul className="llm-notes">
                    {llmFeatures.map((f) => (
                      <li key={f.name}>
                        <strong>{f.name}</strong> ({FEATURE_TYPE_LABEL[f.feature_type]},{" "}
                        {(f.confidence * 100).toFixed(0)}% confidence)
                        {f.feature_type === "holiday" && (
                          <span className={`badge ${f.holiday_confirmed ? "on" : ""}`}>
                            {f.holiday_confirmed ? "calendar-confirmed" : "unconfirmed"}
                          </span>
                        )}
                        <div className="muted llm-rationale">{f.rationale}</div>
                      </li>
                    ))}
                  </ul>
                  <div className="muted llm-models">
                    LLM-recommended models: {llmModels.map((m) => m.name).join(", ")}
                  </div>
                </>
              )}
            </div>

            <div>
              {deltas && (
                <>
                  <h4 className="section-heading">Residual delta (feature effect)</h4>
                  <div className="delta-block">
                    <DeltaRow label="Trend strength" before={deltas.trend_strength_before} after={deltas.trend_strength_after} />
                    <DeltaRow
                      label="Seasonality strength"
                      before={deltas.seasonality_strength_before}
                      after={deltas.seasonality_strength_after}
                    />
                    <div className="delta-row">
                      <span className="delta-label">Stationary</span>
                      <span className="delta-value">{deltas.stationary_before ? "yes" : "no"}</span>
                      <span className="delta-arrow">→</span>
                      <span className="delta-value">{deltas.stationary_after ? "yes" : "no"}</span>
                    </div>
                    <div className="delta-row">
                      <span className="delta-label">R² explained</span>
                      <span className="delta-value delta-good">{(deltas.r_squared * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                </>
              )}

              {refit && (
                <>
                  <h4 className="section-heading">Model metrics (holdout)</h4>
                  <table className="metrics-table">
                    <thead>
                      <tr>
                        <th>Model</th>
                        <th>sMAPE</th>
                        <th>MAE</th>
                        <th>RMSE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(refit.metrics).map(([name, m]) => (
                        <tr key={name} className={name === bestModel ? "best-row" : ""}>
                          <td>{name}</td>
                          <td>{m.smape.toFixed(3)}%</td>
                          <td>{m.mae.toFixed(2)}</td>
                          <td>{m.rmse.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
