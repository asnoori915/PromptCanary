"""
ROUTER SERVICE - Traffic splitting and version selection

This service handles the core canary routing logic:
1. Manages prompt releases and versions
2. Implements traffic splitting between active and canary versions
3. Bootstraps initial releases from existing prompts

This is the "traffic controller" that decides which version of a prompt to use.
"""

import random
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app import models
from app.utils import safe_db_commit, safe_db_flush


def get_or_init_release(db: Session, prompt_id: int) -> Optional[models.PromptRelease]:
    """
    Get existing release or create initial release for a prompt.
    
    This bootstraps the versioning system:
    1. If release exists, return it
    2. If not, create v1 from the original prompt text
    3. Set up initial release with 0% canary
    
    Input: database session, prompt_id
    Output: PromptRelease object or None if prompt doesn't exist
    """
    rel = (db.query(models.PromptRelease)
             .filter(models.PromptRelease.prompt_id == prompt_id)
             .first())
    if rel:
        return rel

    # STEP 1: Bootstrap - create v1 from current Prompt.text
    p = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not p:
        return None
    
    # STEP 2: Create initial version 1 from original prompt
    v1 = models.PromptVersion(prompt_id=prompt_id, version=1, text=p.text, is_active=True)
    safe_db_flush(db, v1)
    
    # STEP 3: Create initial release with 0% canary
    rel = models.PromptRelease(prompt_id=prompt_id, active_version_id=v1.id, canary_percent=0)
    safe_db_commit(db, rel)
    db.refresh(rel)
    return rel


def choose_prompt_text(db: Session, prompt_id: int) -> Tuple[str, bool, Optional[int]]:
    """
    Choose which version of a prompt to use (active vs canary).
    
    This implements the traffic splitting logic:
    1. Get or create the release for this prompt
    2. If canary is active and has percentage > 0, use random roll
    3. Return canary version if roll succeeds, otherwise active version
    
    Input: database session, prompt_id
    Output: (prompt_text, is_canary, version_id)
    """
    rel = get_or_init_release(db, prompt_id)
    if not rel:
        # Fallback to original Prompt.text if no release exists
        p = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
        return (p.text if p else "", False, None)

    # STEP 1: Check if canary is active and has traffic percentage
    if rel.canary_version_id and rel.canary_percent and int(rel.canary_percent) > 0:
        # STEP 2: Random roll to decide canary vs active
        roll = random.randint(1, 100)
        if roll <= int(rel.canary_percent):
            # Canary wins - use canary version
            return (rel.canary_version.text, True, rel.canary_version_id)

    # STEP 3: Default to active version
    return (rel.active_version.text if rel.active_version else "", False, rel.active_version_id)


