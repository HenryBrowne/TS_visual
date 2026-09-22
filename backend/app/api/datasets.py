from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.datasets.models import Dataset, DatasetSourceType
from app.datasets.schemas import DatasetRead

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetRead])
def list_datasets(source_type: DatasetSourceType | None = None, db: Session = Depends(get_db)):
    query = db.query(Dataset)
    if source_type is not None:
        query = query.filter(Dataset.source_type == source_type)
    return query.order_by(Dataset.created_at.desc()).all()
