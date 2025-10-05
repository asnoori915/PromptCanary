from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.analytics import compute_report
from app.schemas import ReportOut

router = APIRouter()

@router.get("", response_model=ReportOut)
def report(window_days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    data = compute_report(db, window_days=window_days, max_compare=20)
    return data
