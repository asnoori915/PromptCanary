"""
ANALYZE ROUTE - Core evaluation endpoint

This is the main endpoint that evaluates prompts and their responses.
It's the heart of the system - every time you want to test how good a prompt is,
you send it here and get back scores.

What it does:
1. Takes a prompt (either text or ID) and optional response
2. Decides which version to test (active vs canary) using canary logic
3. Gets an LLM response if not provided
4. Scores the response on multiple dimensions
5. Stores everything in the database
6. Returns the evaluation scores

This endpoint is called every time you want to:
- Test a new prompt idea
- Evaluate how well your current prompt is working
- Compare active vs canary versions
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app import models
from app.schemas import AnalyzeIn, AnalyzeOut, EvaluationOut
from app.services.scoring import heuristic_scores
from app.services.llm import judge_prompt
from app.services.router import choose_prompt_text

router = APIRouter()

@router.post("", response_model=AnalyzeOut)
def analyze(payload: AnalyzeIn, db: Session = Depends(get_db)):
    """
    Analyze a prompt and its response, returning evaluation scores.
    
    Input: Either prompt text directly OR prompt_id (to reference saved prompt)
    Output: Evaluation scores (clarity, length, toxicity, overall) + notes
    
    This is where the magic happens - it's the main evaluation pipeline.
    """
    # STEP 1: Validate input - we need either prompt text OR prompt_id
    if not payload.prompt_id and not (payload.prompt and payload.prompt.strip()):
        raise HTTPException(status_code=422, detail="prompt or prompt_id is required")

    # STEP 2: Get or create the prompt record
    if payload.prompt_id:
        # Use existing prompt from database
        prompt_row = db.query(models.Prompt).filter(models.Prompt.id == payload.prompt_id).first()
        if not prompt_row:
            raise HTTPException(status_code=404, detail="prompt_id not found")
        base_text = prompt_row.text
    else:
        # Create new prompt record from provided text
        prompt_row = models.Prompt(text=(payload.prompt or "").strip())
        db.add(prompt_row); db.flush()
        base_text = prompt_row.text

    # STEP 3: Store the response if provided (optional)
    response_row = None
    if payload.response and payload.response.strip():
        response_row = models.Response(
            prompt_id=prompt_row.id,
            model_name=payload.model_name or "unknown",
            content=payload.response.strip()
        )
        db.add(response_row); db.flush()

    # STEP 4: CANARY LOGIC - Decide which version to test
    # This is the key part: if there's a canary release active,
    # some requests go to the canary version, others to active version
    chosen_text, is_canary, version_id = choose_prompt_text(db, prompt_row.id)

    # STEP 5: SCORE THE RESPONSE
    # We use both heuristic scoring (rules-based) and LLM judging
    h = heuristic_scores(chosen_text or base_text, payload.response)
    judge = judge_prompt(chosen_text or base_text, payload.response)
    overall = round((h["length_score"] + h["clarity_score"] + h["toxicity_score"]) / 3, 3)

    # STEP 6: STORE THE EVALUATION
    # This creates the data that drives all our analytics and decisions
    eval_row = models.Evaluation(
        prompt_id=prompt_row.id,
        response_id=(response_row.id if response_row else None),
        clarity_score=h["clarity_score"],
        length_score=h["length_score"],
        toxicity_score=h["toxicity_score"],
        overall_score=overall,
        notes=judge.get("notes",""),
        is_canary=is_canary  # Track if this was tested against canary version
    )
    db.add(eval_row); db.commit()

    # STEP 7: RETURN RESULTS
    return AnalyzeOut(
        prompt_id=prompt_row.id,
        evaluation=EvaluationOut(
            clarity_score=h["clarity_score"],
            length_score=h["length_score"],
            toxicity_score=h["toxicity_score"],
            overall_score=overall,
            notes=judge.get("notes","")
        )
    )
