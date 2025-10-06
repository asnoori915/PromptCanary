"""
EVALUATION ROUTE - ML evaluation and model comparison endpoints

This route provides endpoints for:
1. Testing prompts across multiple models
2. Comparing model performance
3. Getting ML metrics and insights
4. Running comprehensive evaluations

This is the "ML evaluation pipeline" that makes the system data-driven.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db import get_db
from app import models
from app.services.model_evaluation import ModelEvaluationService
from app.services.smart_optimization import SmartOptimizationService
from app.utils import handle_db_errors, get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/{prompt_id}/evaluate")
@handle_db_errors
async def evaluate_prompt_models(
    prompt_id: int,
    models_to_test: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Test a prompt across multiple models and compare their performance.
    
    This is the main ML evaluation endpoint that:
    1. Sends the same prompt to multiple models
    2. Compares their outputs using real ML metrics
    3. Stores the results for analysis
    4. Returns which model performed best
    
    Input: prompt_id, optional list of models to test
    Output: Comprehensive evaluation results with model comparison
    """
    # Validate prompt exists
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Run the evaluation
    results = await ModelEvaluationService.run_complete_evaluation(
        db, prompt_id, prompt.text, models_to_test
    )
    
    return results

@router.get("/{prompt_id}/analysis")
@handle_db_errors
def analyze_prompt_patterns(prompt_id: int, db: Session = Depends(get_db)):
    """
    Analyze what makes a prompt work well or poorly.
    
    This looks at all the evaluation data for a prompt and identifies
    patterns, issues, and optimization opportunities.
    
    Input: prompt_id
    Output: Detailed analysis with optimization suggestions
    """
    # Validate prompt exists
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Run the analysis
    analysis = SmartOptimizationService.analyze_prompt_patterns(db, prompt_id)
    
    return analysis

@router.post("/{prompt_id}/smart-optimize")
@handle_db_errors
async def smart_optimize_prompt(prompt_id: int, db: Session = Depends(get_db)):
    """
    Generate optimized versions using data-driven insights.
    
    This is much smarter than the old optimization because it:
    1. Analyzes past evaluation data
    2. Generates multiple optimization strategies
    3. Tests each version to see which is actually better
    4. Returns the best version with confidence scores
    
    Input: prompt_id
    Output: Best optimized version with improvement metrics
    """
    # Validate prompt exists
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Run smart optimization
    results = await SmartOptimizationService.smart_optimize_prompt(db, prompt_id)
    
    return results

@router.get("/{prompt_id}/model-performance")
@handle_db_errors
def get_model_performance(prompt_id: int, db: Session = Depends(get_db)):
    """
    Get historical model performance data for a prompt.
    
    This shows how different models have performed on this prompt
    over time, helping you understand which models work best.
    
    Input: prompt_id
    Output: Model performance history and statistics
    """
    # Validate prompt exists
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Get model evaluations
    evaluations = db.query(models.ModelEvaluation).filter(
        models.ModelEvaluation.prompt_id == prompt_id
    ).order_by(models.ModelEvaluation.created_at.desc()).all()
    
    if not evaluations:
        return {"message": "No model evaluation data available"}
    
    # Aggregate performance by model
    model_stats = {}
    for eval_record in evaluations:
        results = eval_record.results_json or {}
        model_scores = results.get("model_scores", {})
        
        for model_name, scores in model_scores.items():
            if model_name not in model_stats:
                model_stats[model_name] = {
                    "total_tests": 0,
                    "avg_similarity": 0.0,
                    "avg_latency": 0.0,
                    "best_performances": []
                }
            
            model_stats[model_name]["total_tests"] += 1
            model_stats[model_name]["avg_similarity"] += scores.get("avg_similarity", 0.0)
            model_stats[model_name]["avg_latency"] += scores.get("latency_ms", 0.0)
            model_stats[model_name]["best_performances"].append(scores.get("avg_similarity", 0.0))
    
    # Calculate averages
    for model_name in model_stats:
        stats = model_stats[model_name]
        stats["avg_similarity"] /= stats["total_tests"]
        stats["avg_latency"] /= stats["total_tests"]
        stats["best_score"] = max(stats["best_performances"]) if stats["best_performances"] else 0.0
    
    return {
        "prompt_id": prompt_id,
        "total_evaluations": len(evaluations),
        "model_performance": model_stats,
        "recent_evaluations": [
            {
                "id": e.id,
                "best_model": e.best_model,
                "avg_similarity": e.avg_similarity,
                "created_at": e.created_at
            } for e in evaluations[:10]
        ]
    }
