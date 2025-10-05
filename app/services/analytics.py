"""
ANALYTICS SERVICE - System-wide metrics and reporting

This service computes high-level analytics across all prompts and evaluations.
It provides the "executive dashboard" data including:
1. Counts (prompts, responses, evaluations, suggestions)
2. Average scores across all evaluations
3. Feedback statistics (human ratings)
4. Improvement win-rates (original vs optimized prompts)
5. Canary performance metrics

This is used by the /report endpoint to show system-wide performance.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models
from app.services.llm import judge_prompt
import random

def compute_report(db: Session, window_days: int = 30, max_compare: int = 20) -> dict:
    """
    Compute comprehensive analytics report for all prompts over a time window.
    
    This function aggregates data across the entire system:
    1. Counts: prompts, responses, evaluations, suggestions created in window
    2. Average scores: overall, clarity, length across all evaluations
    3. Feedback stats: average human ratings and count
    4. Improvement metrics: win-rate of optimized vs original prompts
    5. Canary metrics: performance comparison and rollback counts
    
    Input: database session, time window in days, max prompts to compare
    Output: comprehensive analytics dict for dashboard/reporting
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=window_days)

    # STEP 1: Count entities created in the time window
    prompts_count = db.query(models.Prompt).filter(models.Prompt.created_at >= start).count()
    responses_count = db.query(models.Response).filter(models.Response.created_at >= start).count()
    evals_count = db.query(models.Evaluation).filter(models.Evaluation.created_at >= start).count()
    suggestions_count = db.query(models.Suggestion).filter(models.Suggestion.created_at >= start).count()

    # STEP 2: Compute average scores across all evaluations in window
    agg = db.query(
        func.avg(models.Evaluation.overall_score),
        func.avg(models.Evaluation.clarity_score),
        func.avg(models.Evaluation.length_score)
    ).filter(models.Evaluation.created_at >= start).one()
    overall_avg = float(agg[0] or 0.0)
    clarity_avg = float(agg[1] or 0.0)
    length_avg = float(agg[2] or 0.0)

    # STEP 3: Compute feedback statistics (human ratings)
    f_agg = db.query(
        func.avg(models.Feedback.rating),
        func.count(models.Feedback.id)
    ).filter(models.Feedback.created_at >= start).one()
    avg_rating = float(f_agg[0] or 0.0)
    ratings_count = int(f_agg[1] or 0)

    # STEP 4: Compute improvement win-rate (optimized vs original prompts)
    # This compares original prompts vs their latest suggestions using LLM evaluation
    prompts_with_suggestions = (db.query(models.Prompt)
                                  .join(models.Suggestion, models.Suggestion.prompt_id == models.Prompt.id)
                                  .order_by(models.Suggestion.created_at.desc())
                                  .limit(max_compare)
                                  .all())

    wins, total = 0, 0
    for p in prompts_with_suggestions:
        # Get the latest suggestion for this prompt
        latest_sug = (sorted(p.suggestions, key=lambda s: s.created_at or now, reverse=True)[0]
                      if p.suggestions else None)
        if not latest_sug:
            continue
        
        # Evaluate both original and suggested prompts using LLM
        orig_eval = judge_prompt(p.text, None)
        sug_eval  = judge_prompt(latest_sug.suggested_text, None)
        orig_score = float(orig_eval.get("overall_score", 0.0) or 0.0)
        sug_score  = float(sug_eval.get("overall_score", 0.0) or 0.0)
        total += 1
        if sug_score > orig_score:
            wins += 1

    win_rate = (wins / total) if total else 0.0

    # STEP 5: Compute canary metrics
    # Count rollbacks in the time window
    rb_count = (db.query(models.RollbackEvent)
                  .filter(models.RollbackEvent.created_at >= start)
                  .count())

    # Compare canary vs active performance across all evaluations
    canary_avg = db.query(func.avg(models.Evaluation.overall_score)).\
        filter(models.Evaluation.created_at >= start, models.Evaluation.is_canary == True).scalar() or 0.0
    active_avg = db.query(func.avg(models.Evaluation.overall_score)).\
        filter(models.Evaluation.created_at >= start, models.Evaluation.is_canary == False).scalar() or 0.0
    canary_win_rate = 1.0 if canary_avg > active_avg else (0.0 if canary_avg < active_avg else 0.5)

    return {
        "window_days": window_days,
        "counts": {
            "prompts": prompts_count,
            "responses": responses_count,
            "evaluations": evals_count,
            "suggestions": suggestions_count
        },
        "scores": {
            "overall_avg": round(overall_avg, 3),
            "clarity_avg": round(clarity_avg, 3),
            "length_avg": round(length_avg, 3)
        },
        "improvement": {
            "optimized_vs_original_win_rate": round(win_rate, 3),
            "sampled": total
        },
        "canary": {
            "avg_canary_overall": round(float(canary_avg), 3),
            "avg_active_overall": round(float(active_avg), 3),
            "naive_canary_win_rate": round(float(canary_win_rate), 3),
            "rollbacks_in_window": int(rb_count),
        },
        "feedback": {
            "avg_rating": round(avg_rating, 3),
            "ratings_count": ratings_count
        }
    }
