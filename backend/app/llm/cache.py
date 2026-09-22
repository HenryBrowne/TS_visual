"""LLM diagnostics are expensive (real API calls) and don't change unless
the series' profile does, so this cache is lazily populated -- compute
once per series on first access, not upfront for every series in the
dataset.
"""

from sqlalchemy.orm import Session

from app.llm.client import run_diagnostics
from app.llm.models import SeriesDiagnosticCache
from app.llm.schema import ConfirmedSeriesDiagnostic
from app.profiling.schema import SeriesProfile


def get_cached_diagnostic(db: Session, series_id: str) -> ConfirmedSeriesDiagnostic | None:
    row = db.get(SeriesDiagnosticCache, series_id)
    if row is None:
        return None
    return ConfirmedSeriesDiagnostic(
        series_id=series_id,
        narrative=row.narrative,
        suggested_features=row.suggested_features,
        suggested_models=row.suggested_models,
    )


def get_or_compute_diagnostic(db: Session, profile: SeriesProfile) -> ConfirmedSeriesDiagnostic:
    cached = get_cached_diagnostic(db, profile.series_id)
    if cached is not None:
        return cached

    results = run_diagnostics([profile])
    diagnostic = results[0]

    row = SeriesDiagnosticCache(
        series_id=profile.series_id,
        narrative=diagnostic.narrative,
        suggested_features=[f.model_dump() for f in diagnostic.suggested_features],
        suggested_models=[m.model_dump() for m in diagnostic.suggested_models],
    )
    db.add(row)
    db.commit()

    return diagnostic
