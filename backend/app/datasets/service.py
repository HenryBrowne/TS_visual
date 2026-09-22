from sqlalchemy.orm import Session

from app.datasets.models import Dataset, DatasetFormat, DatasetSourceType, DatasetStatus


def get_or_create_reference_dataset(db: Session, name: str, format: DatasetFormat) -> Dataset:
    """Reference datasets (M4/M5) are seeded once, not re-created per run --
    re-running the seed script should reuse the existing row (and its id, so
    already-cached profiles/diagnostics stay valid) rather than duplicating it.
    """
    existing = (
        db.query(Dataset)
        .filter(Dataset.name == name, Dataset.source_type == DatasetSourceType.reference)
        .one_or_none()
    )
    if existing is not None:
        return existing

    dataset = Dataset(
        name=name,
        source_type=DatasetSourceType.reference,
        has_benchmark_scores=True,
        format=format,
        status=DatasetStatus.processing,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def resolve_dataset_id(db: Session, dataset_id: str | None) -> str | None:
    """Passes an explicit dataset_id through unchanged. When omitted, falls
    back to the most recently created ready dataset -- this app has no
    user/session concept, so "most-recently-used" degrades to
    "most-recently-created" globally. Returns None if no ready dataset
    exists yet.
    """
    if dataset_id is not None:
        return dataset_id

    latest = (
        db.query(Dataset)
        .filter(Dataset.status == DatasetStatus.ready)
        .order_by(Dataset.created_at.desc())
        .first()
    )
    return latest.id if latest is not None else None
