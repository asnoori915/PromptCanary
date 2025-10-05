"""
CANARY SERVICE - Traffic splitting and automatic rollback logic

This service handles the core canary deployment functionality:
1. Compares canary vs active version performance
2. Automatically rolls back canary if it performs poorly
3. Sends webhook notifications for rollback events
4. Computes performance metrics over time windows

This is the "brain" that decides when to promote or rollback canary versions.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import json
import urllib.request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app import models
from app.config import CANARY_MIN_SAMPLES, CANARY_THRESHOLD, WEBHOOK_URL


def _post_webhook(message: dict) -> None:
    """
    Send webhook notification (best-effort, failures are ignored).
    
    This allows external systems to be notified of important events
    like canary rollbacks without blocking the main flow.
    """
    if not WEBHOOK_URL:
        return
    try:
        data = json.dumps(message).encode("utf-8")
        req = urllib.request.Request(WEBHOOK_URL, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        # Best-effort; ignore webhook failures
        pass


def compute_canary_vs_active_avg(db: Session, prompt_id: int, window_days: int = 30) -> Tuple[float, float, int, int]:
    """
    Compute average scores for canary vs active versions over a time window.
    
    This function:
    1. Gets all evaluations for the prompt in the time window
    2. Separates canary vs active evaluations (using is_canary flag)
    3. Computes average overall_score for each group
    4. Returns averages and sample counts
    
    Input: database session, prompt_id, time window in days
    Output: (canary_avg, active_avg, canary_count, active_count)
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=window_days)
    
    # STEP 1: Get canary evaluations (is_canary=True)
    canary_q = (db.query(models.Evaluation)
                  .filter(models.Evaluation.prompt_id == prompt_id,
                          models.Evaluation.created_at >= start,
                          models.Evaluation.is_canary == True)
                  .order_by(desc(models.Evaluation.id)))
    
    # STEP 2: Get active evaluations (is_canary=False)
    active_q = (db.query(models.Evaluation)
                  .filter(models.Evaluation.prompt_id == prompt_id,
                          models.Evaluation.created_at >= start,
                          models.Evaluation.is_canary == False)
                  .order_by(desc(models.Evaluation.id)))

    canary = canary_q.all()
    active = active_q.all()

    # STEP 3: Compute averages (handle empty lists)
    canary_avg = sum((e.overall_score or 0.0) for e in canary) / len(canary) if canary else 0.0
    active_avg = sum((e.overall_score or 0.0) for e in active) / len(active) if active else 0.0
    return float(canary_avg), float(active_avg), len(canary), len(active)


def check_canary_and_maybe_rollback(db: Session, prompt_id: int,
                                    min_samples: Optional[int] = None,
                                    threshold: Optional[float] = None,
                                    window_days: int = 30) -> dict:
    """
    Check canary performance and automatically rollback if it's performing poorly.
    
    This is the core canary decision logic:
    1. Check if there's an active canary release
    2. Ensure we have enough samples for statistical significance
    3. Compare canary vs active performance
    4. Auto-rollback if canary is significantly worse
    5. Send webhook notification if rollback occurs
    
    Input: database session, prompt_id, optional min_samples/threshold overrides
    Output: dict with check results and any actions taken
    """
    min_samples = int(min_samples or CANARY_MIN_SAMPLES)
    threshold = float(threshold or CANARY_THRESHOLD)

    # STEP 1: Check if there's an active canary to evaluate
    rel = (db.query(models.PromptRelease)
             .filter(models.PromptRelease.prompt_id == prompt_id)
             .first())
    if not rel or not rel.canary_version_id or int(rel.canary_percent) == 0:
        return {"checked": True, "rolled_back": False, "reason": "no active canary"}

    # STEP 2: Compute performance averages
    canary_avg, active_avg, n_canary, n_active = compute_canary_vs_active_avg(db, prompt_id, window_days)
    total = n_canary
    
    # STEP 3: Check if we have enough samples for statistical significance
    if total < min_samples:
        return {"checked": True, "rolled_back": False, "reason": f"insufficient samples: {total}/{min_samples}",
                "canary_avg": canary_avg, "active_avg": active_avg}

    # STEP 4: Compare performance and rollback if canary is significantly worse
    # Rollback if: canary_avg < active_avg * threshold
    if canary_avg + 1e-9 < active_avg * threshold:
        # Create rollback event for audit trail
        evt = models.RollbackEvent(
            prompt_id=prompt_id,
            from_version_id=rel.canary_version_id,
            to_version_id=rel.active_version_id,
            reason=f"auto-rollback: canary_avg {canary_avg:.3f} < active_avg {active_avg:.3f} * threshold {threshold:.2f}"
        )
        
        # Stop the canary (set percentage to 0, clear canary version)
        rel.canary_version_id = None
        rel.canary_percent = 0
        db.add(evt); db.add(rel); db.commit()

        # STEP 5: Send webhook notification
        _post_webhook({
            "type": "prompt_canary_rollback",
            "prompt_id": prompt_id,
            "message": evt.reason,
            "canary_avg": round(canary_avg,3),
            "active_avg": round(active_avg,3)
        })
        return {"checked": True, "rolled_back": True, "reason": evt.reason,
                "canary_avg": canary_avg, "active_avg": active_avg}

    # STEP 6: Canary is performing acceptably
    return {"checked": True, "rolled_back": False, "reason": "canary acceptable",
            "canary_avg": canary_avg, "active_avg": active_avg}


