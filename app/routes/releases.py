"""
RELEASES ROUTE - Canary deployment and version management

This is the most important route - it manages canary releases and version control.
It's the "deployment pipeline" for your prompts.

What it does:
1. Creates releases with canary percentages
2. Manages active vs canary versions
3. Handles rollbacks when canary performs poorly
4. Provides status and monitoring

This is where you control the "traffic splitting" that makes canary testing work.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db import get_db
from app import models

router = APIRouter()


class ReleaseIn(BaseModel):
    suggestion_id: int | None = None
    canary_percent: int = 10  # 0..100


from app.services.canary import check_canary_and_maybe_rollback


@router.post("/{prompt_id}/release")
def release_prompt(prompt_id: int = Path(..., gt=0), payload: ReleaseIn = None, db: Session = Depends(get_db), background: BackgroundTasks = None):
    """
    Create a canary release for a prompt.
    
    Input: prompt_id, suggestion_id (optional), canary_percent (0-100)
    Output: Release status with active/canary versions and percentage
    
    This is the core canary deployment endpoint:
    1. Takes a suggestion (improved prompt) 
    2. Creates a new version from that suggestion
    3. Sets up canary traffic splitting
    4. Starts background monitoring
    """
    # STEP 1: Validate the prompt exists
    p = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="prompt not found")

    # STEP 2: Get the suggestion to release
    # Either use the provided suggestion_id or get the latest one
    s = None
    if payload.suggestion_id:
        s = db.query(models.Suggestion).filter(models.Suggestion.id == payload.suggestion_id).first()
        if not s or s.prompt_id != prompt_id:
            raise HTTPException(status_code=400, detail="suggestion invalid for this prompt")
    else:
        s = (db.query(models.Suggestion)
                .filter(models.Suggestion.prompt_id == prompt_id)
                .order_by(models.Suggestion.id.desc())
                .first())
        if not s:
            raise HTTPException(status_code=400, detail="no suggestions exist for this prompt")

    # STEP 3: Find or create the release record
    # This manages the active/canary version state
    rel = (db.query(models.PromptRelease)
             .filter(models.PromptRelease.prompt_id == prompt_id)
             .first())
    if not rel:
        # First release - create v1 from original prompt
        v1 = models.PromptVersion(prompt_id=prompt_id, version=1, text=p.text, is_active=True)
        db.add(v1); db.flush()
        rel = models.PromptRelease(prompt_id=prompt_id, active_version_id=v1.id, canary_percent=0)
        db.add(rel); db.flush()

    # STEP 4: Create new version from suggestion
    # Calculate next version number (increment from existing versions)
    next_version = 1
    if rel.active_version:
        next_version = max(next_version, rel.active_version.version + 1)
    if rel.canary_version:
        next_version = max(next_version, rel.canary_version.version + 1)

    # Create the canary version
    v_canary = models.PromptVersion(prompt_id=prompt_id, version=next_version, text=s.suggested_text, is_active=False)
    db.add(v_canary); db.flush()

    # STEP 5: Update release with canary configuration
    # This is what controls the traffic splitting
    rel.canary_version_id = v_canary.id
    rel.canary_percent = max(0, min(100, int(payload.canary_percent)))
    db.add(rel); db.commit()

    # STEP 6: Start background monitoring
    # This will check canary performance and auto-rollback if needed
    if background is not None:
        background.add_task(check_canary_and_maybe_rollback, db, prompt_id, None, None)

    return {"prompt_id": prompt_id, "active_version": rel.active_version.version if rel.active_version else None,
            "canary_version": v_canary.version, "canary_percent": rel.canary_percent}


class RollbackIn(BaseModel):
    reason: str | None = None


@router.post("/{prompt_id}/rollback")
def rollback(prompt_id: int = Path(..., gt=0), payload: RollbackIn | None = None, db: Session = Depends(get_db)):
    """
    Rollback a canary release (stop using canary version).
    
    Input: prompt_id, optional reason
    Output: Confirmation of rollback
    
    This manually stops the canary and reverts to the active version:
    1. Records the rollback event for audit trail
    2. Sets canary_percent to 0
    3. Clears canary_version_id
    """
    # STEP 1: Validate there's a canary to rollback
    rel = (db.query(models.PromptRelease)
             .filter(models.PromptRelease.prompt_id == prompt_id)
             .first())
    if not rel or not rel.canary_version_id:
        raise HTTPException(status_code=400, detail="no canary to rollback")

    # STEP 2: Record the rollback event for audit trail
    # This creates a permanent record of why/when rollback happened
    evt = models.RollbackEvent(
        prompt_id=prompt_id,
        from_version_id=rel.canary_version_id,
        to_version_id=rel.active_version_id,
        reason=(payload.reason if payload else None)
    )
    
    # STEP 3: Stop the canary (set percentage to 0, clear canary version)
    rel.canary_version_id = None
    rel.canary_percent = 0
    db.add(evt); db.add(rel); db.commit()
    return {"ok": True}


@router.get("/{prompt_id}/status")
def status(prompt_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """
    Get the current release status for a prompt.
    
    Input: prompt_id
    Output: Current active/canary versions, canary percentage, recent rollbacks
    
    This shows you:
    - Which version is currently active
    - Which version is in canary (if any)
    - What percentage of traffic goes to canary
    - Recent rollback history
    """
    # STEP 1: Get the current release state
    rel = (db.query(models.PromptRelease)
             .filter(models.PromptRelease.prompt_id == prompt_id)
             .first())
    if not rel:
        raise HTTPException(status_code=404, detail="no release state for prompt")

    # STEP 2: Get recent rollback history for context
    recent_rb = (db.query(models.RollbackEvent)
                   .filter(models.RollbackEvent.prompt_id == prompt_id)
                   .order_by(models.RollbackEvent.id.desc())
                   .limit(5)
                   .all())

    # STEP 3: Return comprehensive status
    return {
        "prompt_id": prompt_id,
        "active_version": rel.active_version.version if rel.active_version else None,
        "canary_version": rel.canary_version.version if rel.canary_version else None,
        "canary_percent": rel.canary_percent,
        "recent_rollbacks": [
            {
                "from": rb.from_version.version if rb.from_version else None,
                "to": rb.to_version.version if rb.to_version else None,
                "reason": rb.reason,
                "created_at": rb.created_at,
            } for rb in recent_rb
        ]
    }


@router.post("/{prompt_id}/check")
def manual_check(prompt_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """
    Manually trigger a canary performance check.
    
    Input: prompt_id
    Output: Check results and any actions taken
    
    This manually runs the canary evaluation logic:
    - Compares canary vs active performance
    - Auto-promotes canary if it's performing better
    - Auto-rollbacks canary if it's performing worse
    - Returns the decision and reasoning
    """
    result = check_canary_and_maybe_rollback(db, prompt_id)
    return result


