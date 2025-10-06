"""
SIMPLE EVALUATION ROUTE - Simplified ML evaluation endpoints

This provides simplified versions of the ML evaluation endpoints that work
without complex async operations and rate limit issues.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app import models
from app.services.ml_metrics import ml_metrics
from app.utils import handle_db_errors, get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("/{prompt_id}/analysis")
@handle_db_errors
def analyze_prompt_patterns(prompt_id: int, db: Session = Depends(get_db)):
    """
    Analyze what makes a prompt work well or poorly (simplified version).
    
    This looks at all the evaluation data for a prompt and identifies
    patterns, issues, and optimization opportunities.
    """
    # Validate prompt exists
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Get all evaluations for this prompt
    evaluations = db.query(models.Evaluation).filter(
        models.Evaluation.prompt_id == prompt_id
    ).all()
    
    if not evaluations:
        return {
            "prompt_id": prompt_id,
            "message": "No evaluation data available yet",
            "suggestions": [
                "Run more evaluations to get analysis data",
                "Try different prompts to compare performance"
            ]
        }
    
    # Analyze patterns
    high_scores = [e for e in evaluations if e.overall_score and e.overall_score > 0.7]
    low_scores = [e for e in evaluations if e.overall_score and e.overall_score < 0.4]
    
    # Analyze prompt characteristics
    prompt_text = prompt.text
    word_count = len(prompt_text.split())
    has_questions = "?" in prompt_text
    has_examples = "example" in prompt_text.lower() or "for instance" in prompt_text.lower()
    has_constraints = any(word in prompt_text.lower() for word in ["must", "should", "require", "limit"])
    
    # Get recent feedback
    recent_feedback = db.query(models.Feedback).filter(
        models.Feedback.prompt_id == prompt_id
    ).limit(10).all()
    
    avg_rating = sum(f.rating for f in recent_feedback) / len(recent_feedback) if recent_feedback else 0
    
    # Generate suggestions
    suggestions = []
    if word_count > 100:
        suggestions.append("Consider shortening the prompt - longer prompts often score lower")
    elif word_count < 20:
        suggestions.append("Add more detail - very short prompts often lack clarity")
    
    if len(low_scores) > len(evaluations) * 0.3:
        suggestions.append("This prompt consistently scores low - consider major restructuring")
    
    if not has_examples:
        suggestions.append("Consider adding an example to improve clarity")
    
    if not has_constraints:
        suggestions.append("Add specific requirements or constraints")
    
    return {
        "prompt_id": prompt_id,
        "prompt_characteristics": {
            "word_count": word_count,
            "has_questions": has_questions,
            "has_examples": has_examples,
            "has_constraints": has_constraints
        },
        "performance_analysis": {
            "total_evaluations": len(evaluations),
            "high_score_count": len(high_scores),
            "low_score_count": len(low_scores),
            "avg_score": sum(e.overall_score for e in evaluations if e.overall_score) / len(evaluations),
            "avg_human_rating": avg_rating
        },
        "optimization_suggestions": suggestions
    }

@router.post("/{prompt_id}/test-metrics")
@handle_db_errors
def test_ml_metrics(prompt_id: int, db: Session = Depends(get_db)):
    """
    Test ML metrics on a prompt (simplified version).
    
    This demonstrates the ML metrics without calling multiple models.
    """
    # Validate prompt exists
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Get a sample response if available
    sample_response = db.query(models.Response).filter(
        models.Response.prompt_id == prompt_id
    ).first()
    
    if sample_response:
        # Test ML metrics with actual response
        metrics = ml_metrics.evaluate_response_quality(
            prompt.text, 
            sample_response.content,
            expected_length=50
        )
        
        return {
            "prompt_id": prompt_id,
            "prompt_text": prompt.text,
            "sample_response": sample_response.content,
            "ml_metrics": metrics,
            "message": "ML metrics computed successfully"
        }
    else:
        # Test with heuristic scoring only
        from app.services.scoring import heuristic_scores
        h_scores = heuristic_scores(prompt.text)
        
        return {
            "prompt_id": prompt_id,
            "prompt_text": prompt.text,
            "heuristic_scores": h_scores,
            "message": "No sample response available - showing heuristic scores only"
        }

@router.get("/{prompt_id}/performance")
@handle_db_errors
def get_prompt_performance(prompt_id: int, db: Session = Depends(get_db)):
    """
    Get performance data for a prompt (simplified version).
    """
    # Validate prompt exists
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Get evaluations
    evaluations = db.query(models.Evaluation).filter(
        models.Evaluation.prompt_id == prompt_id
    ).all()
    
    # Get responses
    responses = db.query(models.Response).filter(
        models.Response.prompt_id == prompt_id
    ).all()
    
    # Get feedback
    feedback = db.query(models.Feedback).filter(
        models.Feedback.prompt_id == prompt_id
    ).all()
    
    return {
        "prompt_id": prompt_id,
        "prompt_text": prompt.text,
        "statistics": {
            "total_evaluations": len(evaluations),
            "total_responses": len(responses),
            "total_feedback": len(feedback),
            "avg_score": sum(e.overall_score for e in evaluations if e.overall_score) / len(evaluations) if evaluations else 0,
            "avg_rating": sum(f.rating for f in feedback) / len(feedback) if feedback else 0
        },
        "recent_evaluations": [
            {
                "id": e.id,
                "overall_score": e.overall_score,
                "is_canary": e.is_canary,
                "created_at": e.created_at
            } for e in evaluations[-5:]  # Last 5 evaluations
        ]
    }
