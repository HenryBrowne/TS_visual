from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.leaderboard import get_leaderboard_rows

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("")
def get_leaderboard(db: Session = Depends(get_db)):
    return get_leaderboard_rows(db)
