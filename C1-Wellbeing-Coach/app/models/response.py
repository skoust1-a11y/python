from pydantic import BaseModel
from typing import List, Optional

class Recommendation(BaseModel):
    activity: str
    message: str

class Response(BaseModel):
    interaction_id: str
    emotion: Optional[str] = None
    confidence: Optional[float] = None
    message: str
    recommendations: Recommendation
    
 