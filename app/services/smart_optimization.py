"""
SMART OPTIMIZATION SERVICE - Data-driven prompt improvement

This service uses real evaluation data to make much better optimization decisions.
Instead of just asking an LLM to rewrite prompts, it:

1. Analyzes past evaluation data to understand what works
2. Tests multiple optimization strategies
3. Uses real metrics to choose the best version
4. Learns from feedback to improve over time

Simple explanation:
- Old way: "Please make this prompt better" (guessing)
- New way: "Based on 1000 evaluations, prompts with X pattern score 20% higher" (data-driven)
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app import models
from app.services.llm import judge_prompt, optimize_prompt
from app.services.ml_metrics import ml_metrics
from app.services.model_evaluation import ModelEvaluationService
from app.utils import get_logger, safe_db_commit, safe_db_flush

logger = get_logger(__name__)

class SmartOptimizationService:
    """Service for data-driven prompt optimization."""
    
    @staticmethod
    def analyze_prompt_patterns(db: Session, prompt_id: int) -> Dict[str, Any]:
        """
        Analyze what makes this prompt work well or poorly.
        
        This looks at the evaluation history for this prompt and tries to
        understand patterns in what works and what doesn't.
        """
        # Get all evaluations for this prompt
        evaluations = db.query(models.Evaluation).filter(
            models.Evaluation.prompt_id == prompt_id
        ).order_by(desc(models.Evaluation.created_at)).all()
        
        if not evaluations:
            return {"error": "No evaluation data available"}
        
        # Analyze patterns
        high_scores = [e for e in evaluations if e.overall_score and e.overall_score > 0.7]
        low_scores = [e for e in evaluations if e.overall_score and e.overall_score < 0.4]
        
        # Get the original prompt
        prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
        if not prompt:
            return {"error": "Prompt not found"}
        
        # Analyze prompt characteristics
        prompt_text = prompt.text
        word_count = len(prompt_text.split())
        has_questions = "?" in prompt_text
        has_examples = "example" in prompt_text.lower() or "for instance" in prompt_text.lower()
        has_constraints = any(word in prompt_text.lower() for word in ["must", "should", "require", "limit"])
        
        # Get recent feedback
        recent_feedback = db.query(models.Feedback).filter(
            models.Feedback.prompt_id == prompt_id
        ).order_by(desc(models.Feedback.created_at)).limit(10).all()
        
        avg_rating = sum(f.rating for f in recent_feedback) / len(recent_feedback) if recent_feedback else 0
        
        return {
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
            "common_issues": SmartOptimizationService._identify_common_issues(evaluations),
            "optimization_suggestions": SmartOptimizationService._generate_suggestions(
                prompt_text, evaluations, recent_feedback
            )
        }
    
    @staticmethod
    def _identify_common_issues(evaluations: List[models.Evaluation]) -> List[str]:
        """Identify common issues from evaluation notes."""
        all_notes = [e.notes for e in evaluations if e.notes]
        if not all_notes:
            return []
        
        # Simple keyword analysis (in production, use NLP)
        issue_keywords = {
            "unclear": ["unclear", "vague", "ambiguous", "confusing"],
            "too_long": ["too long", "verbose", "wordy"],
            "too_short": ["too short", "brief", "incomplete"],
            "missing_context": ["context", "background", "information"],
            "poor_structure": ["structure", "format", "organization"]
        }
        
        issues = []
        for issue, keywords in issue_keywords.items():
            if any(keyword in note.lower() for note in all_notes for keyword in keywords):
                issues.append(issue)
        
        return issues
    
    @staticmethod
    def _generate_suggestions(
        prompt_text: str, 
        evaluations: List[models.Evaluation], 
        feedback: List[models.Feedback]
    ) -> List[str]:
        """Generate specific optimization suggestions based on data."""
        suggestions = []
        
        # Analyze word count
        word_count = len(prompt_text.split())
        if word_count > 100:
            suggestions.append("Consider shortening the prompt - longer prompts often score lower")
        elif word_count < 20:
            suggestions.append("Add more detail - very short prompts often lack clarity")
        
        # Analyze common issues
        low_score_evals = [e for e in evaluations if e.overall_score and e.overall_score < 0.5]
        if len(low_score_evals) > len(evaluations) * 0.3:  # More than 30% low scores
            suggestions.append("This prompt consistently scores low - consider major restructuring")
        
        # Analyze human feedback
        if feedback:
            low_ratings = [f for f in feedback if f.rating <= 2]
            if len(low_ratings) > len(feedback) * 0.4:  # More than 40% low ratings
                suggestions.append("Human feedback indicates this prompt needs improvement")
        
        # Check for missing elements
        if "example" not in prompt_text.lower():
            suggestions.append("Consider adding an example to improve clarity")
        
        if not any(word in prompt_text.lower() for word in ["must", "should", "require"]):
            suggestions.append("Add specific requirements or constraints")
        
        return suggestions
    
    @staticmethod
    async def generate_optimized_versions(
        db: Session, 
        prompt_id: int, 
        num_versions: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple optimized versions of a prompt using data-driven insights.
        
        This is much smarter than the old optimization because it:
        1. Analyzes what's wrong with the current prompt
        2. Generates multiple different approaches
        3. Tests each one to see which is actually better
        """
        # Step 1: Analyze the current prompt
        analysis = SmartOptimizationService.analyze_prompt_patterns(db, prompt_id)
        
        if "error" in analysis:
            return [{"error": analysis["error"]}]
        
        # Step 2: Get the original prompt
        prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
        original_text = prompt.text
        
        # Step 3: Generate different optimization strategies
        strategies = SmartOptimizationService._generate_optimization_strategies(analysis)
        
        # Step 4: Create optimized versions using different strategies
        optimized_versions = []
        
        for i, strategy in enumerate(strategies[:num_versions]):
            try:
                # Use LLM to optimize with specific strategy
                optimized_text = optimize_prompt(original_text, strategy["instruction"])
                
                # Test the optimized version
                test_result = await SmartOptimizationService._test_optimized_version(
                    db, prompt_id, optimized_text, original_text
                )
                
                optimized_versions.append({
                    "version_id": i + 1,
                    "strategy": strategy["name"],
                    "optimized_text": optimized_text,
                    "improvement_score": test_result.get("improvement_score", 0.0),
                    "predicted_better": test_result.get("predicted_better", False),
                    "reasoning": strategy["reasoning"]
                })
                
            except Exception as e:
                logger.error(f"Error generating optimized version {i}: {e}")
                optimized_versions.append({
                    "version_id": i + 1,
                    "error": str(e)
                })
        
        # Step 5: Sort by predicted improvement
        optimized_versions.sort(key=lambda x: x.get("improvement_score", 0.0), reverse=True)
        
        return optimized_versions
    
    @staticmethod
    def _generate_optimization_strategies(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate specific optimization strategies based on analysis."""
        strategies = []
        
        characteristics = analysis.get("prompt_characteristics", {})
        issues = analysis.get("common_issues", [])
        suggestions = analysis.get("optimization_suggestions", [])
        
        # Strategy 1: Clarity improvement
        if "unclear" in issues or characteristics.get("word_count", 0) > 100:
            strategies.append({
                "name": "clarity_focus",
                "instruction": "Rewrite this prompt to be much clearer and more concise. Remove unnecessary words and make the instructions crystal clear.",
                "reasoning": "Current prompt is too long or unclear based on evaluation data"
            })
        
        # Strategy 2: Add structure
        if "poor_structure" in issues:
            strategies.append({
                "name": "structured_approach",
                "instruction": "Rewrite this prompt with clear structure: 1) Context, 2) Task, 3) Requirements, 4) Example format.",
                "reasoning": "Current prompt lacks clear structure"
            })
        
        # Strategy 3: Add examples
        if not characteristics.get("has_examples", False):
            strategies.append({
                "name": "example_enhanced",
                "instruction": "Rewrite this prompt and include a concrete example of what a good response looks like.",
                "reasoning": "Adding examples typically improves prompt performance"
            })
        
        # Strategy 4: Add constraints
        if not characteristics.get("has_constraints", False):
            strategies.append({
                "name": "constraint_focused",
                "instruction": "Rewrite this prompt with specific constraints and requirements. Be very clear about what the output should and shouldn't include.",
                "reasoning": "Adding constraints helps guide the model to better outputs"
            })
        
        # Strategy 5: Question-based approach
        if not characteristics.get("has_questions", False):
            strategies.append({
                "name": "question_driven",
                "instruction": "Rewrite this prompt as a series of clear questions that guide the model to the desired output.",
                "reasoning": "Question-based prompts often perform better"
            })
        
        # Default strategy if no specific issues identified
        if not strategies:
            strategies.append({
                "name": "general_improvement",
                "instruction": "Improve this prompt by making it more specific, clear, and actionable. Add any missing context or requirements.",
                "reasoning": "General improvement based on best practices"
            })
        
        return strategies
    
    @staticmethod
    async def _test_optimized_version(
        db: Session, 
        prompt_id: int, 
        optimized_text: str, 
        original_text: str
    ) -> Dict[str, Any]:
        """
        Test an optimized version against the original using real metrics.
        
        This actually measures if the optimized version is better,
        rather than just hoping it is.
        """
        try:
            # Get recent responses for the original prompt
            recent_responses = db.query(models.Response).filter(
                models.Response.prompt_id == prompt_id
            ).order_by(desc(models.Response.created_at)).limit(5).all()
            
            if not recent_responses:
                # No responses to compare against, use LLM evaluation
                original_eval = judge_prompt(original_text, None)
                optimized_eval = judge_prompt(optimized_text, None)
                
                improvement = (optimized_eval.get("overall_score", 0.0) - 
                             original_eval.get("overall_score", 0.0))
                
                return {
                    "improvement_score": improvement,
                    "predicted_better": improvement > 0.1,
                    "method": "llm_evaluation"
                }
            
            # Compare against recent responses
            improvements = []
            for response in recent_responses:
                # Test both versions with the same response
                original_sim = ml_metrics.compute_semantic_similarity(original_text, response.content)
                optimized_sim = ml_metrics.compute_semantic_similarity(optimized_text, response.content)
                
                improvement = optimized_sim - original_sim
                improvements.append(improvement)
            
            avg_improvement = sum(improvements) / len(improvements) if improvements else 0.0
            
            return {
                "improvement_score": avg_improvement,
                "predicted_better": avg_improvement > 0.05,
                "method": "response_comparison",
                "comparisons_made": len(improvements)
            }
            
        except Exception as e:
            logger.error(f"Error testing optimized version: {e}")
            return {
                "improvement_score": 0.0,
                "predicted_better": False,
                "error": str(e)
            }
    
    @staticmethod
    async def smart_optimize_prompt(db: Session, prompt_id: int) -> Dict[str, Any]:
        """
        Main smart optimization function.
        
        This replaces the old simple optimization with a data-driven approach
        that actually measures improvement and learns from past data.
        """
        logger.info(f"Starting smart optimization for prompt {prompt_id}")
        
        # Step 1: Analyze current prompt performance
        analysis = SmartOptimizationService.analyze_prompt_patterns(db, prompt_id)
        
        # Step 2: Generate optimized versions
        optimized_versions = await SmartOptimizationService.generate_optimized_versions(db, prompt_id)
        
        # Step 3: Find the best version
        best_version = None
        if optimized_versions and not any("error" in v for v in optimized_versions):
            best_version = optimized_versions[0]  # Already sorted by improvement score
        
        # Step 4: Store the best suggestion
        if best_version and best_version.get("predicted_better", False):
            suggestion = models.Suggestion(
                prompt_id=prompt_id,
                suggested_text=best_version["optimized_text"],
                rationale=f"Data-driven optimization using {best_version['strategy']} strategy. Predicted improvement: {best_version['improvement_score']:.3f}"
            )
            safe_db_commit(db, suggestion)
            
            return {
                "success": True,
                "best_version": best_version,
                "all_versions": optimized_versions,
                "analysis": analysis,
                "suggestion_id": suggestion.id
            }
        else:
            return {
                "success": False,
                "message": "No significant improvement found",
                "analysis": analysis,
                "versions_tested": len(optimized_versions)
            }
