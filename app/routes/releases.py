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
    p = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="prompt not found")

    # Determine suggestion: use provided id or latest suggestion for this prompt
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

    # find or create release row
    rel = (db.query(models.PromptRelease)
             .filter(models.PromptRelease.prompt_id == prompt_id)
             .first())
    if not rel:
        # create v1 from original
        v1 = models.PromptVersion(prompt_id=prompt_id, version=1, text=p.text, is_active=True)
        db.add(v1); db.flush()
        rel = models.PromptRelease(prompt_id=prompt_id, active_version_id=v1.id, canary_percent=0)
        db.add(rel); db.flush()

    # create new version from suggestion text
    next_version = 1
    if rel.active_version:
        next_version = max(next_version, rel.active_version.version + 1)
    if rel.canary_version:
        next_version = max(next_version, rel.canary_version.version + 1)

    v_canary = models.PromptVersion(prompt_id=prompt_id, version=next_version, text=s.suggested_text, is_active=False)
    db.add(v_canary); db.flush()

    rel.canary_version_id = v_canary.id
    rel.canary_percent = max(0, min(100, int(payload.canary_percent)))
    db.add(rel); db.commit()

    # Kick off background canary check so it's evaluated soon after release
    if background is not None:
        background.add_task(check_canary_and_maybe_rollback, db, prompt_id, None, None)

    return {"prompt_id": prompt_id, "active_version": rel.active_version.version if rel.active_version else None,
            "canary_version": v_canary.version, "canary_percent": rel.canary_percent}


class RollbackIn(BaseModel):
    reason: str | None = None


@router.post("/{prompt_id}/rollback")
def rollback(prompt_id: int = Path(..., gt=0), payload: RollbackIn | None = None, db: Session = Depends(get_db)):
    rel = (db.query(models.PromptRelease)
             .filter(models.PromptRelease.prompt_id == prompt_id)
             .first())
    if not rel or not rel.canary_version_id:
        raise HTTPException(status_code=400, detail="no canary to rollback")

    evt = models.RollbackEvent(
        prompt_id=prompt_id,
        from_version_id=rel.canary_version_id,
        to_version_id=rel.active_version_id,
        reason=(payload.reason if payload else None)
    )
    rel.canary_version_id = None
    rel.canary_percent = 0
    db.add(evt); db.add(rel); db.commit()
    return {"ok": True}


@router.get("/{prompt_id}/status")
def status(prompt_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    rel = (db.query(models.PromptRelease)
             .filter(models.PromptRelease.prompt_id == prompt_id)
             .first())
    if not rel:
        raise HTTPException(status_code=404, detail="no release state for prompt")

    recent_rb = (db.query(models.RollbackEvent)
                   .filter(models.RollbackEvent.prompt_id == prompt_id)
                   .order_by(models.RollbackEvent.id.desc())
                   .limit(5)
                   .all())

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
    result = check_canary_and_maybe_rollback(db, prompt_id)
    return result


