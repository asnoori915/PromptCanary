from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app import models

router = APIRouter()

@router.get("")
def history(prompt_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    p = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="prompt not found")

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
    suggestions = [
        {
            "text": s.suggested_text,
            "rationale": s.rationale,
            "created_at": s.created_at
        } for s in p.suggestions
    ]
    return {"prompt": p.text, "evaluations": evals, "suggestions": suggestions}
