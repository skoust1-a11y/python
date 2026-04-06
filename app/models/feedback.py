from pydantic import BaseModel
from typing import Optional

class Feedback(BaseModel):
    interaction_id: str
    rating: Optional[int] = None  # Optional rating (1-5 scale)
    feedback: Optional[str] = None  # Optional general feedback text
    comment: Optional[str] = None  # Optional user comment