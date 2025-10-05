from pydantic import BaseModel
from typing import Optional

class AnalyzeIn(BaseModel):
    prompt: str
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
