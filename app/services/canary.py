from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import json
import urllib.request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app import models
from app.config import CANARY_MIN_SAMPLES, CANARY_THRESHOLD, WEBHOOK_URL


def _post_webhook(message: dict) -> None:
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
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=window_days)
    canary_q = (db.query(models.Evaluation)
                  .filter(models.Evaluation.prompt_id == prompt_id,
                          models.Evaluation.created_at >= start,
                          models.Evaluation.is_canary == True)
                  .order_by(desc(models.Evaluation.id)))
    active_q = (db.query(models.Evaluation)
                  .filter(models.Evaluation.prompt_id == prompt_id,
                          models.Evaluation.created_at >= start,
                          models.Evaluation.is_canary == False)
                  .order_by(desc(models.Evaluation.id)))

    canary = canary_q.all()
    active = active_q.all()

    canary_avg = sum((e.overall_score or 0.0) for e in canary) / len(canary) if canary else 0.0
    active_avg = sum((e.overall_score or 0.0) for e in active) / len(active) if active else 0.0
    return float(canary_avg), float(active_avg), len(canary), len(active)


def check_canary_and_maybe_rollback(db: Session, prompt_id: int,
                                    min_samples: Optional[int] = None,
                                    threshold: Optional[float] = None,
                                    window_days: int = 30) -> dict:
    min_samples = int(min_samples or CANARY_MIN_SAMPLES)
    threshold = float(threshold or CANARY_THRESHOLD)

    rel = (db.query(models.PromptRelease)
             .filter(models.PromptRelease.prompt_id == prompt_id)
             .first())
    if not rel or not rel.canary_version_id or int(rel.canary_percent) == 0:
        return {"checked": True, "rolled_back": False, "reason": "no active canary"}

    canary_avg, active_avg, n_canary, n_active = compute_canary_vs_active_avg(db, prompt_id, window_days)
    total = n_canary
    if total < min_samples:
        return {"checked": True, "rolled_back": False, "reason": f"insufficient samples: {total}/{min_samples}",
                "canary_avg": canary_avg, "active_avg": active_avg}

    if canary_avg + 1e-9 < active_avg * threshold:
        evt = models.RollbackEvent(
            prompt_id=prompt_id,
            from_version_id=rel.canary_version_id,
            to_version_id=rel.active_version_id,
            reason=f"auto-rollback: canary_avg {canary_avg:.3f} < active_avg {active_avg:.3f} * threshold {threshold:.2f}"
        )
        rel.canary_version_id = None
        rel.canary_percent = 0
        db.add(evt); db.add(rel); db.commit()

        _post_webhook({
            "type": "prompt_canary_rollback",
            "prompt_id": prompt_id,
            "message": evt.reason,
            "canary_avg": round(canary_avg,3),
            "active_avg": round(active_avg,3)
        })
        return {"checked": True, "rolled_back": True, "reason": evt.reason,
                "canary_avg": canary_avg, "active_avg": active_avg}

    return {"checked": True, "rolled_back": False, "reason": "canary acceptable",
            "canary_avg": canary_avg, "active_avg": active_avg}


