"""
PYDANTIC SCHEMAS - Request/response data validation

This file defines the data structures for API requests and responses using Pydantic.
These schemas provide:
1. Input validation for API endpoints
2. Type safety and documentation
3. Automatic JSON serialization/deserialization
4. Clear API contracts

Each schema corresponds to specific API endpoints and their expected data formats.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from app.utils import Constants

class AnalyzeIn(BaseModel):
    """
    Input schema for the analyze endpoint.
    
    Either provide prompt text directly OR reference an existing prompt by ID.
    Response and model_name are optional for cases where you already have the response.
    """
    prompt: Optional[str] = Field(None, min_length=1, max_length=Constants.MAX_PROMPT_LENGTH, description="Direct prompt text")
    prompt_id: Optional[int] = Field(None, gt=0, description="Reference to existing prompt")
    response: Optional[str] = Field(None, max_length=Constants.MAX_RESPONSE_LENGTH, description="Optional response (if already generated)")
    model_name: Optional[str] = Field(None, max_length=Constants.MAX_MODEL_NAME_LENGTH, description="Which LLM generated the response")
    
    @validator('prompt_id', always=True)
    def validate_prompt_or_id(cls, v, values):
        if not values.get('prompt') and not v:
            raise ValueError('Either prompt or prompt_id must be provided')
        return v

class EvaluationOut(BaseModel):
    """
    Output schema for evaluation scores.
    
    All scores are on a 0-1 scale where higher is better.
    Notes contain LLM-generated improvement suggestions.
    """
    clarity_score: float  # How clear/unambiguous the prompt is
    length_score: float   # Optimal length scoring
    toxicity_score: float # Content safety scoring
    overall_score: float  # Combined/weighted overall score
    notes: str  # LLM-generated improvement suggestions

class AnalyzeOut(BaseModel):
    """
    Output schema for the analyze endpoint.
    
    Returns the prompt_id and the complete evaluation results.
    """
    prompt_id: int  # The prompt that was evaluated
    evaluation: EvaluationOut  # The evaluation scores and notes

class FeedbackIn(BaseModel):
    """
    Input schema for human feedback submission.
    
    Requires a prompt_id and rating. Response_id and comment are optional.
    """
    prompt_id: int = Field(..., gt=0, description="Which prompt this feedback is for")
    response_id: Optional[int] = Field(None, gt=0, description="Optional: specific response being rated")
    rating: int = Field(..., ge=1, le=5, description="Human rating 1-5 (1=bad, 5=excellent)")
    comment: Optional[str] = Field(None, max_length=Constants.MAX_COMMENT_LENGTH, description="Optional human comment")

class FeedbackAck(BaseModel):
    """
    Simple acknowledgment that feedback was received and stored.
    """
    ok: bool  # True if feedback was successfully stored

class ReportOut(BaseModel):
    """
    Output schema for the analytics report endpoint.
    
    Contains comprehensive system-wide metrics and statistics.
    """
    window_days: int  # Time window for the report
    counts: dict  # Entity counts (prompts, responses, evaluations, etc.)
    scores: dict  # Average scores across all evaluations
    improvement: dict  # Improvement metrics and win-rates
    feedback: dict  # Human feedback statistics