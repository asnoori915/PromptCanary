"""
HISTORY ROUTE - View prompt evolution over time

This endpoint shows you the complete history of a prompt - all evaluations,
suggestions, and how it has evolved over time.

What it does:
1. Takes a prompt_id
2. Returns all evaluations (scores over time)
3. Returns all suggestions (improvement attempts)
4. Shows the current prompt text

This is your "dashboard" to see how a prompt is performing.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app import models

router = APIRouter()

@router.get("")
def history(prompt_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    """
    Get the complete history of a prompt - evaluations and suggestions.
    
    Input: prompt_id (must exist in database)
    Output: Prompt text + all evaluations + all suggestions
    
    This shows you:
    - How the prompt has scored over time
    - What suggestions have been made
    - The evolution of your prompt's performance
    """
    # STEP 1: Validate the prompt exists
    p = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="prompt not found")

    # STEP 2: Get all evaluations (scores over time)
    # This shows you how the prompt has performed historically
    evals = [
        {
            "overall": e.overall_score,
            "clarity": e.clarity_score,
            "length": e.length_score,
            "toxicity": e.toxicity_score,
            "notes": e.notes,
            "created_at": e.created_at
        } for e in p.evaluations
    ]
    
    # STEP 3: Get all suggestions (improvement attempts)
    # This shows you what improvements have been suggested
    suggestions = [
        {
            "text": s.suggested_text,
            "rationale": s.rationale,
            "created_at": s.created_at
        } for s in p.suggestions
    ]
    
    # STEP 4: Return everything together
    # This gives you the complete picture of your prompt's journey
    return {"prompt": p.text, "evaluations": evals, "suggestions": suggestions}
