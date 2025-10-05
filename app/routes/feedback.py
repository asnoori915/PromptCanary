from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app import models
from app.schemas import FeedbackIn, FeedbackAck

router = APIRouter()

@router.post("", response_model=FeedbackAck)
def leave_feedback(payload: FeedbackIn, db: Session = Depends(get_db)):
    # ensure prompt exists
    p = db.query(models.Prompt).filter(models.Prompt.id == payload.prompt_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="prompt not found")

    # if response_id provided, ensure it exists & belongs to this prompt
    if payload.response_id:
        r = db.query(models.Response).filter(models.Response.id == payload.response_id).first()
        if not r or r.prompt_id != payload.prompt_id:
            raise HTTPException(status_code=400, detail="response_id invalid for this prompt")

    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=422, detail="rating must be 1..5")

    fb = models.Feedback(
        prompt_id=payload.prompt_id,
        response_id=payload.response_id,
        rating=payload.rating,
        comment=(payload.comment or "").strip() or None
    )
    db.add(fb)
    db.commit()
    return FeedbackAck(ok=True)
