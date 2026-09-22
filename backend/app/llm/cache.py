"""LLM diagnostics are expensive (real API calls) and don't change unless
the series' profile does, so this cache is lazily populated -- compute
once per series on first access, not upfront for every series in the
dataset. Keyed by (dataset_id, series_id) for the same reason as the
profile cache: series_id alone isn't globally unique once user uploads
exist.
"""

from sqlalchemy.orm import Session

from app.llm.client import run_diagnostics
from app.llm.models import SeriesDiagnosticCache
from app.llm.schema import ConfirmedSeriesDiagnostic
from app.profiling.schema import SeriesProfile


def get_cached_diagnostic(db: Session, dataset_id: str, series_id: str) -> ConfirmedSeriesDiagnostic | None:
    row = db.get(SeriesDiagnosticCache, (dataset_id, series_id))
    if row is None:
        return None
    return ConfirmedSeriesDiagnostic(
        series_id=series_id,
        narrative=row.narrative,
        suggested_features=row.suggested_features,
        suggested_models=row.suggested_models,
    )


def store_diagnostics_batch(db: Session, dataset_id: str, diagnostics: list[ConfirmedSeriesDiagnostic]) -> None:
    """Bulk-writes results from a single batched run_diagnostics() call --
    used by the CSV import job, which profiles+diagnoses every series
    upfront rather than lazily on first workbench access (unlike the
    reference-dataset path)."""
    for diagnostic in diagnostics:
        row = db.get(SeriesDiagnosticCache, (dataset_id, diagnostic.series_id))
        if row is None:
            row = SeriesDiagnosticCache(dataset_id=dataset_id, series_id=diagnostic.series_id, narrative="", suggested_features=[], suggested_models=[])
            db.add(row)
        row.narrative = diagnostic.narrative
        row.suggested_features = [f.model_dump() for f in diagnostic.suggested_features]
        row.suggested_models = [m.model_dump() for m in diagnostic.suggested_models]
    db.commit()


def get_or_compute_diagnostic(db: Session, dataset_id: str, profile: SeriesProfile) -> ConfirmedSeriesDiagnostic:
    cached = get_cached_diagnostic(db, dataset_id, profile.series_id)
    if cached is not None:
        return cached

    results = run_diagnostics([profile])
    diagnostic = results[0]

    row = SeriesDiagnosticCache(
        dataset_id=dataset_id,
        series_id=profile.series_id,
        narrative=diagnostic.narrative,
        suggested_features=[f.model_dump() for f in diagnostic.suggested_features],
        suggested_models=[m.model_dump() for m in diagnostic.suggested_models],
    )
    db.add(row)
    db.commit()

    return diagnostic
