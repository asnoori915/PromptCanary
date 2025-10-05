from pydantic import BaseModel
from typing import Optional

class AnalyzeIn(BaseModel):
    prompt: Optional[str] = None
    prompt_id: Optional[int] = None
    response: Optional[str] = None
    model_name: Optional[str] = None

class EvaluationOut(BaseModel):
    clarity_score: float
    length_score: float
    toxicity_score: float
    overall_score: float
    notes: str

class AnalyzeOut(BaseModel):
    prompt_id: int
    evaluation: EvaluationOut

class FeedbackIn(BaseModel):
    prompt_id: int
    response_id: Optional[int] = None
    rating: int  # 1..5
    comment: Optional[str] = None

class FeedbackAck(BaseModel):
    ok: bool

class ReportOut(BaseModel):
    window_days: int
    counts: dict
    scores: dict
    improvement: dict
    feedback: dict