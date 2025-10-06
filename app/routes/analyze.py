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
from app.schemas import AnalyzeIn, AnalyzeOut
from app.services.prompt_service import PromptService
from app.services.async_service import AsyncService
from app.utils import handle_db_errors, get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("", response_model=AnalyzeOut)
@handle_db_errors
async def analyze(payload: AnalyzeIn, db: Session = Depends(get_db)):
    """
    Analyze a prompt and its response, returning evaluation scores.
    
    Input: Either prompt text directly OR prompt_id (to reference saved prompt)
    Output: Evaluation scores (clarity, length, toxicity, overall) + notes
    
    This is where the magic happens - it's the main evaluation pipeline.
    """
    # Delegate to service layer for business logic
    prompt_id, evaluation = PromptService.analyze_prompt(db, payload)
    
    return AnalyzeOut(
        prompt_id=prompt_id,
        evaluation=evaluation
    )
