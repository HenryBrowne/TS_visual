from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.datasets.service import resolve_dataset_id
from app.models.leaderboard import get_leaderboard_rows

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("")
def get_leaderboard(dataset_id: str | None = None, db: Session = Depends(get_db)):
    resolved_dataset_id = resolve_dataset_id(db, dataset_id)
    if resolved_dataset_id is None:
        raise HTTPException(status_code=400, detail="No ready dataset available")
    return get_leaderboard_rows(db, dataset_id=resolved_dataset_id)
