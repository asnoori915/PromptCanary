from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app import models
from app.services.llm import optimize_prompt

router = APIRouter()

@router.get("")
def optimize(prompt_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="prompt not found")

    last_eval = (db.query(models.Evaluation)
                   .filter(models.Evaluation.prompt_id == prompt_id)
                   .order_by(models.Evaluation.id.desc())
                   .first())
    notes = last_eval.notes if last_eval else "Improve clarity; add constraints and success criteria."

    rewritten = optimize_prompt(prompt.text, notes)

    s = models.Suggestion(prompt_id=prompt_id, suggested_text=rewritten, rationale=notes)
    db.add(s); db.commit()
    return {"prompt_id": prompt_id, "suggested_text": rewritten}
