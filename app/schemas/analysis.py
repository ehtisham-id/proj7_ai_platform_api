from pydantic import BaseModel
from typing import List, Dict, Any

class AnalysisResponse(BaseModel):
    analysis_id: int
    summary: Dict[str, Any]
    charts_url: List[str]
    insights: List[str]
