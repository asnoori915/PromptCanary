"""
PROMPT SERVICE - Business logic for prompt operations

This service contains the core business logic for prompt operations,
separated from the route handlers for better testability and reusability.
"""

from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app import models
from app.schemas import AnalyzeIn, EvaluationOut
from app.services.scoring import heuristic_scores
from app.services.llm import judge_prompt
from app.services.router import choose_prompt_text
from app.utils import safe_db_commit, safe_db_flush, get_logger, calculate_overall_score

logger = get_logger(__name__)

class PromptService:
    """Service class for prompt-related business logic."""
    
    @staticmethod
    def create_or_get_prompt(db: Session, payload: AnalyzeIn) -> Tuple[models.Prompt, str]:
        """
        Create a new prompt or get existing one by ID.
        
        Returns:
            Tuple of (prompt_model, base_text)
        """
        if payload.prompt_id:
            # Use existing prompt from database
            prompt_row = db.query(models.Prompt).filter(models.Prompt.id == payload.prompt_id).first()
            if not prompt_row:
                raise ValueError("prompt_id not found")
            return prompt_row, prompt_row.text
        else:
            # Create new prompt record from provided text
            prompt_row = models.Prompt(text=payload.prompt.strip())
            safe_db_flush(db, prompt_row)
            return prompt_row, prompt_row.text
    
    @staticmethod
    def create_response(db: Session, prompt_id: int, payload: AnalyzeIn) -> Optional[models.Response]:
        """
        Create a response record if response text is provided.
        
        Returns:
            Response model or None if no response provided
        """
        if not payload.response or not payload.response.strip():
            return None
            
        response_row = models.Response(
            prompt_id=prompt_id,
            model_name=payload.model_name or "unknown",
            content=payload.response.strip()
        )
        safe_db_flush(db, response_row)
        return response_row
    
    @staticmethod
    def evaluate_prompt_response(prompt_text: str, response_text: Optional[str]) -> Dict[str, Any]:
        """
        Evaluate a prompt and response using both heuristic and LLM scoring.
        
        Returns:
            Dictionary with all scores and evaluation data
        """
        # Get heuristic scores (fast, rule-based)
        h_scores = heuristic_scores(prompt_text, response_text)
        
        # Get LLM evaluation (slower, more sophisticated)
        llm_eval = judge_prompt(prompt_text, response_text)
        
        # Calculate overall score
        overall = calculate_overall_score(h_scores)
        
        return {
            "heuristic_scores": h_scores,
            "llm_evaluation": llm_eval,
            "overall_score": overall,
            "notes": llm_eval.get("notes", "")
        }
    
    @staticmethod
    def create_evaluation(
        db: Session, 
        prompt_id: int, 
        response_id: Optional[int], 
        evaluation_data: Dict[str, Any],
        is_canary: bool
    ) -> models.Evaluation:
        """
        Create and store an evaluation record.
        
        Returns:
            Created evaluation model
        """
        eval_row = models.Evaluation(
            prompt_id=prompt_id,
            response_id=response_id,
            clarity_score=evaluation_data["heuristic_scores"]["clarity_score"],
            length_score=evaluation_data["heuristic_scores"]["length_score"],
            toxicity_score=evaluation_data["heuristic_scores"]["toxicity_score"],
            overall_score=evaluation_data["overall_score"],
            notes=evaluation_data["notes"],
            is_canary=is_canary
        )
        safe_db_commit(db, eval_row)
        return eval_row
    
    @staticmethod
    def analyze_prompt(db: Session, payload: AnalyzeIn) -> Tuple[int, EvaluationOut]:
        """
        Complete prompt analysis workflow.
        
        Returns:
            Tuple of (prompt_id, evaluation_results)
        """
        # Step 1: Get or create prompt
        prompt_row, base_text = PromptService.create_or_get_prompt(db, payload)
        
        # Step 2: Create response if provided
        response_row = PromptService.create_response(db, prompt_row.id, payload)
        
        # Step 3: Choose which version to test (canary logic)
        chosen_text, is_canary, version_id = choose_prompt_text(db, prompt_row.id)
        
        # Step 4: Evaluate the prompt/response
        evaluation_data = PromptService.evaluate_prompt_response(
            chosen_text or base_text, 
            payload.response
        )
        
        # Step 5: Store evaluation
        eval_row = PromptService.create_evaluation(
            db, 
            prompt_row.id, 
            response_row.id if response_row else None,
            evaluation_data,
            is_canary
        )
        
        # Step 6: Return results
        evaluation_out = EvaluationOut(
            clarity_score=evaluation_data["heuristic_scores"]["clarity_score"],
            length_score=evaluation_data["heuristic_scores"]["length_score"],
            toxicity_score=evaluation_data["heuristic_scores"]["toxicity_score"],
            overall_score=evaluation_data["overall_score"],
            notes=evaluation_data["notes"]
        )
        
        return prompt_row.id, evaluation_out
