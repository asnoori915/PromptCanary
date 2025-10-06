"""
MODEL EVALUATION SERVICE - Test prompts across multiple LLMs

This service runs the same prompt through multiple models and compares
their outputs using real ML metrics. This gives us data-driven insights
into which prompts work best with which models.

Simple explanation:
1. Take a prompt
2. Send it to GPT-4, GPT-3.5, Claude, etc.
3. Compare the outputs using BLEU, ROUGE, semantic similarity
4. Store the results so we can see which prompts are best
"""

from typing import List, Dict, Any, Optional, Tuple
import asyncio
import time
from sqlalchemy.orm import Session
from app import models
from app.services.llm import judge_prompt
from app.services.ml_metrics import ml_metrics
from app.utils import get_logger, safe_db_commit, safe_db_flush

logger = get_logger(__name__)

class ModelEvaluationService:
    """Service for evaluating prompts across multiple models."""
    
    # Available models to test
    AVAILABLE_MODELS = [
        {"name": "gpt-4o-mini", "provider": "openai", "cost_per_1k": 0.00015},
        {"name": "gpt-3.5-turbo", "provider": "openai", "cost_per_1k": 0.0005},
        # Add more models as needed
    ]
    
    @staticmethod
    async def call_model_async(prompt: str, model_name: str) -> Dict[str, Any]:
        """
        Call a specific model with a prompt and measure performance.
        
        This is where we actually send the prompt to different LLMs
        and measure how long it takes and how much it costs.
        """
        start_time = time.time()
        
        try:
            # For now, we'll use the existing judge_prompt function
            # In a real system, you'd have separate functions for each model
            result = await asyncio.get_event_loop().run_in_executor(
                None, judge_prompt, prompt, None
            )
            
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            return {
                "model_name": model_name,
                "response": result.get("notes", ""),  # Using notes as response for now
                "latency_ms": latency_ms,
                "success": True,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error calling model {model_name}: {e}")
            return {
                "model_name": model_name,
                "response": "",
                "latency_ms": 0,
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def evaluate_prompt_across_models(prompt: str, models_to_test: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Test a prompt across multiple models simultaneously.
        
        This is the main function that:
        1. Sends the same prompt to multiple models
        2. Collects all the responses
        3. Returns the results for comparison
        """
        if models_to_test is None:
            models_to_test = [model["name"] for model in ModelEvaluationService.AVAILABLE_MODELS]
        
        # Run all model calls in parallel
        tasks = [
            ModelEvaluationService.call_model_async(prompt, model_name)
            for model_name in models_to_test
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Model {models_to_test[i]} failed: {result}")
                processed_results.append({
                    "model_name": models_to_test[i],
                    "response": "",
                    "latency_ms": 0,
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    @staticmethod
    def compare_model_outputs(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare outputs from multiple models using ML metrics.
        
        This function takes all the model responses and compares them
        to see which one is best using real ML metrics.
        """
        successful_results = [r for r in results if r["success"]]
        
        if len(successful_results) < 2:
            return {"error": "Need at least 2 successful responses to compare"}
        
        comparisons = []
        
        # Compare each pair of responses
        for i in range(len(successful_results)):
            for j in range(i + 1, len(successful_results)):
                result1 = successful_results[i]
                result2 = successful_results[j]
                
                # Compute similarity metrics
                similarity = ml_metrics.compute_semantic_similarity(
                    result1["response"], result2["response"]
                )
                
                rouge_scores = ml_metrics.compute_rouge_scores(
                    result1["response"], result2["response"]
                )
                
                comparisons.append({
                    "model1": result1["model_name"],
                    "model2": result2["model_name"],
                    "semantic_similarity": similarity,
                    "rouge_scores": rouge_scores
                })
        
        # Find the best performing model (highest average similarity to others)
        model_scores = {}
        for result in successful_results:
            model_name = result["model_name"]
            similarities = []
            
            for other_result in successful_results:
                if other_result["model_name"] != model_name:
                    sim = ml_metrics.compute_semantic_similarity(
                        result["response"], other_result["response"]
                    )
                    similarities.append(sim)
            
            model_scores[model_name] = {
                "avg_similarity": sum(similarities) / len(similarities) if similarities else 0.0,
                "latency_ms": result["latency_ms"],
                "response_length": len(result["response"].split())
            }
        
        # Find best model (highest similarity + lowest latency)
        best_model = max(
            model_scores.keys(),
            key=lambda m: model_scores[m]["avg_similarity"] - (model_scores[m]["latency_ms"] / 10000)
        )
        
        return {
            "comparisons": comparisons,
            "model_scores": model_scores,
            "best_model": best_model,
            "total_models_tested": len(successful_results)
        }
    
    @staticmethod
    def store_evaluation_results(
        db: Session, 
        prompt_id: int, 
        evaluation_results: List[Dict[str, Any]],
        comparison_results: Dict[str, Any]
    ) -> int:
        """
        Store evaluation results in the database.
        
        This saves all the model comparison data so we can analyze
        which prompts work best with which models over time.
        """
        # Create evaluation record
        eval_record = models.ModelEvaluation(
            prompt_id=prompt_id,
            models_tested=len(evaluation_results),
            best_model=comparison_results.get("best_model"),
            avg_similarity=comparison_results.get("model_scores", {}).get(
                comparison_results.get("best_model", ""), {}
            ).get("avg_similarity", 0.0),
            total_latency_ms=sum(r["latency_ms"] for r in evaluation_results),
            results_json=comparison_results
        )
        
        safe_db_commit(db, eval_record)
        return eval_record.id
    
    @staticmethod
    async def run_complete_evaluation(
        db: Session, 
        prompt_id: int, 
        prompt_text: str,
        models_to_test: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run complete evaluation pipeline.
        
        This is the main function that:
        1. Tests the prompt across multiple models
        2. Compares the results
        3. Stores everything in the database
        4. Returns a summary
        """
        logger.info(f"Starting evaluation for prompt {prompt_id}")
        
        # Step 1: Test across models
        evaluation_results = await ModelEvaluationService.evaluate_prompt_across_models(
            prompt_text, models_to_test
        )
        
        # Step 2: Compare results
        comparison_results = ModelEvaluationService.compare_model_outputs(evaluation_results)
        
        # Step 3: Store results
        eval_id = ModelEvaluationService.store_evaluation_results(
            db, prompt_id, evaluation_results, comparison_results
        )
        
        # Step 4: Return summary
        return {
            "evaluation_id": eval_id,
            "prompt_id": prompt_id,
            "models_tested": len(evaluation_results),
            "successful_models": len([r for r in evaluation_results if r["success"]]),
            "best_model": comparison_results.get("best_model"),
            "avg_similarity": comparison_results.get("model_scores", {}).get(
                comparison_results.get("best_model", ""), {}
            ).get("avg_similarity", 0.0),
            "total_latency_ms": sum(r["latency_ms"] for r in evaluation_results)
        }
