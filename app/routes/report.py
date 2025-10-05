"""
REPORT ROUTE - Analytics and metrics dashboard

This endpoint provides high-level analytics across all prompts.
It's your "executive dashboard" showing overall system performance.

What it does:
1. Takes a time window (default 30 days)
2. Aggregates scores, counts, and trends across all prompts
3. Shows improvement metrics and feedback summaries

This is where you see the big picture of how your prompts are performing.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.analytics import compute_report
from app.schemas import ReportOut

router = APIRouter()

@router.get("", response_model=ReportOut)
def report(window_days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """
    Get analytics report for all prompts over a time window.
    
    Input: window_days (1-365, default 30)
    Output: Aggregated metrics, counts, scores, improvement trends
    
    This shows you:
    - Total evaluations, responses, feedback counts
    - Average scores across all prompts
    - Improvement trends over time
    - Feedback summaries
    """
    # STEP 1: Compute analytics using the analytics service
    # This aggregates all the data across prompts and time windows
    data = compute_report(db, window_days=window_days, max_compare=20)
    return data
