"""
FEEDBACK ROUTE - Collect human feedback on prompts

This endpoint lets humans rate and comment on prompt performance.
It's the "human in the loop" part of the system.

What it does:
1. Takes a prompt_id and optional response_id
2. Accepts a rating (1-5) and optional comment
3. Stores the feedback for analytics and decision-making

This is how you get human validation of your prompt improvements.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app import models
from app.schemas import FeedbackIn, FeedbackAck

router = APIRouter()

@router.post("", response_model=FeedbackAck)
def leave_feedback(payload: FeedbackIn, db: Session = Depends(get_db)):
    """
    Submit human feedback on a prompt or response.
    
    Input: prompt_id, optional response_id, rating (1-5), optional comment
    Output: Confirmation that feedback was stored
    
    This allows humans to:
    - Rate prompt performance (1-5 scale)
    - Add comments about what worked/didn't work
    - Provide feedback on specific responses
    """
    # STEP 1: Validate the prompt exists
    p = db.query(models.Prompt).filter(models.Prompt.id == payload.prompt_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="prompt not found")

    # STEP 2: If response_id provided, validate it exists and belongs to this prompt
    # This ensures feedback is properly linked
    if payload.response_id:
        r = db.query(models.Response).filter(models.Response.id == payload.response_id).first()
        if not r or r.prompt_id != payload.prompt_id:
            raise HTTPException(status_code=400, detail="response_id invalid for this prompt")

    # STEP 3: Validate rating is in valid range (1-5)
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=422, detail="rating must be 1..5")

    # STEP 4: Store the feedback
    # This creates the human validation data that drives decisions
    fb = models.Feedback(
        prompt_id=payload.prompt_id,
        response_id=payload.response_id,
        rating=payload.rating,
        comment=(payload.comment or "").strip() or None
    )
    db.add(fb)
    db.commit()
    return FeedbackAck(ok=True)
