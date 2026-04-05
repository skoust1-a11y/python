from pydantic import BaseModel

class Feedback(BaseModel):
    interaction_id: str
    rating: int
    comment: str = None