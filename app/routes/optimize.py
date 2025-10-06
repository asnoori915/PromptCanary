"""
OPTIMIZE ROUTE - Prompt improvement suggestions

This endpoint helps you improve prompts by generating better versions.
It's the "brain" that suggests how to make your prompts better.

What it does:
1. Takes a prompt_id (reference to existing prompt)
2. Looks at recent evaluation feedback to understand what's wrong
3. Uses LLM to generate an improved version of the prompt
4. Stores the suggestion for later use in canary releases

This is where you get new prompt ideas to test.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app import models
from app.services.llm import optimize_prompt
from app.services.smart_optimization import SmartOptimizationService
from app.utils import handle_db_errors, get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("")
@handle_db_errors
async def optimize(prompt_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    """
    Generate an optimized version of a prompt based on recent feedback.
    
    Input: prompt_id (must exist in database)
    Output: New suggested prompt text
    
    This endpoint:
    1. Looks at recent evaluation notes to understand issues
    2. Calls LLM to rewrite the prompt better
    3. Stores the suggestion for potential canary release
    """
    # Use the new smart optimization system
    results = await SmartOptimizationService.smart_optimize_prompt(db, prompt_id)
    
    if results.get("success", False):
        return {
            "prompt_id": prompt_id,
            "suggested_text": results["best_version"]["optimized_text"],
            "improvement_score": results["best_version"]["improvement_score"],
            "strategy_used": results["best_version"]["strategy"],
            "reasoning": results["best_version"]["reasoning"],
            "suggestion_id": results["suggestion_id"]
        }
    else:
        # Fallback to old method if smart optimization fails
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
        
        return {
            "prompt_id": prompt_id,
            "suggested_text": rewritten,
            "method": "fallback_optimization",
            "suggestion_id": s.id
        }
