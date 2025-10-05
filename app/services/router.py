import random
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app import models


def get_or_init_release(db: Session, prompt_id: int) -> Optional[models.PromptRelease]:
    rel = (db.query(models.PromptRelease)
             .filter(models.PromptRelease.prompt_id == prompt_id)
             .first())
    if rel:
        return rel

    # bootstrap: create v1 from current Prompt.text
    p = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not p:
        return None
    v1 = models.PromptVersion(prompt_id=prompt_id, version=1, text=p.text, is_active=True)
    db.add(v1); db.flush()
    rel = models.PromptRelease(prompt_id=prompt_id, active_version_id=v1.id, canary_percent=0)
    db.add(rel); db.commit(); db.refresh(rel)
    return rel


def choose_prompt_text(db: Session, prompt_id: int) -> Tuple[str, bool, Optional[int]]:
    """
    Returns (text, is_canary, version_id)
    """
    rel = get_or_init_release(db, prompt_id)
    if not rel:
        # Fallback to Prompt.text
        p = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
        return (p.text if p else "", False, None)

    if rel.canary_version_id and rel.canary_percent and int(rel.canary_percent) > 0:
        roll = random.randint(1, 100)
        if roll <= int(rel.canary_percent):
            return (rel.canary_version.text, True, rel.canary_version_id)

    # default to active
    return (rel.active_version.text if rel.active_version else "", False, rel.active_version_id)


