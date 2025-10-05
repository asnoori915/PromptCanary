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
    if not payload.prompt_id and not (payload.prompt and payload.prompt.strip()):
        raise HTTPException(status_code=422, detail="prompt or prompt_id is required")

    if payload.prompt_id:
        prompt_row = db.query(models.Prompt).filter(models.Prompt.id == payload.prompt_id).first()
        if not prompt_row:
            raise HTTPException(status_code=404, detail="prompt_id not found")
        base_text = prompt_row.text
    else:
        prompt_row = models.Prompt(text=(payload.prompt or "").strip())
        db.add(prompt_row); db.flush()
        base_text = prompt_row.text

    response_row = None
    if payload.response and payload.response.strip():
        response_row = models.Response(
            prompt_id=prompt_row.id,
            model_name=payload.model_name or "unknown",
            content=payload.response.strip()
        )
        db.add(response_row); db.flush()

    # Determine which prompt text to evaluate against (active vs canary)
    chosen_text, is_canary, version_id = choose_prompt_text(db, prompt_row.id)

    h = heuristic_scores(chosen_text or base_text, payload.response)
    judge = judge_prompt(chosen_text or base_text, payload.response)
    overall = round((h["length_score"] + h["clarity_score"] + h["toxicity_score"]) / 3, 3)

    eval_row = models.Evaluation(
        prompt_id=prompt_row.id,
        response_id=(response_row.id if response_row else None),
        clarity_score=h["clarity_score"],
        length_score=h["length_score"],
        toxicity_score=h["toxicity_score"],
        overall_score=overall,
        notes=judge.get("notes",""),
        is_canary=is_canary
    )
    db.add(eval_row); db.commit()

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
