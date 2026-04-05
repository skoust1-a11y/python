from pydantic import BaseModel
from typing import List, Optional

class Response(BaseModel):
    emotion: Optional[str] = None
    confidence: Optional[float] = None
    message: str
    recommendations: List[str] = []