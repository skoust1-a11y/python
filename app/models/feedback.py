from pydantic import BaseModel

class Feedback(BaseModel):
    user_id: str
    rating: int
    comment: str = None