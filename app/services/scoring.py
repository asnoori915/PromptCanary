"""
SCORING SERVICE - Rule-based prompt evaluation

This service provides fast, deterministic scoring of prompts using simple heuristics.
It complements the LLM-based evaluation in llm.py by providing:
1. Length scoring (optimal around 40 words)
2. Clarity scoring (penalizes vague terms)
3. Toxicity scoring (placeholder for content safety)

These scores are combined with LLM scores for comprehensive evaluation.
"""

from typing import Dict, Optional
from app.utils import Constants, round_score

def heuristic_scores(prompt: str, response: Optional[str] = None) -> Dict[str, float]:
    """
    Compute heuristic scores for a prompt using simple rules.
    
    This provides fast, deterministic scoring that doesn't require API calls:
    1. Length score: Optimal around 40 words, penalizes too short/long
    2. Clarity score: Penalizes vague terms like "maybe", "sort of"
    3. Toxicity score: Placeholder (always 1.0, could add content filtering)
    
    Input: prompt text, optional response (not used in current implementation)
    Output: dict with length_score, clarity_score, toxicity_score (0-1 range)
    """
    # STEP 1: Length scoring - optimal around 40 words
    words = len(prompt.split())
    length_score = max(0.0, min(1.0, 1 - abs(words - Constants.OPTIMAL_PROMPT_LENGTH) / 60))
    
    # STEP 2: Clarity scoring - penalize vague terms
    vague_terms = ["maybe","sort of","kind of","roughly","approximately"]
    vagueness = sum(prompt.lower().count(t) for t in vague_terms)
    clarity_score = max(0.0, 1.0 - Constants.VAGUENESS_PENALTY * vagueness)
    
    # STEP 3: Toxicity scoring - placeholder for content safety
    # TODO: Could add actual content filtering here
    toxicity_score = 1.0
    
    return {
        "length_score": round_score(length_score),
        "clarity_score": round_score(clarity_score),
        "toxicity_score": round_score(toxicity_score)
    }
