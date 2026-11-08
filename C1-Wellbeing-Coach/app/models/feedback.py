from pydantic import BaseModel,field_validator
from typing import Optional

class Feedback(BaseModel):
    interaction_id: str
    rating: Optional[int] = None  # Optional rating (1-5 scale)
    feedback: Optional[str] = None  # Optional general feedback text
    comment: Optional[str] = None  # Optional user comment


    @field_validator('interaction_id')
    @classmethod
    def interact_valid(cls, value: str):
        if not value:
            raise ValueError('Empty Interaction ID')

        if not value.isdigit():
            raise ValueError('Interaction ID must be numeric')

        if int(value) < 0:
            raise ValueError('Invalid Interaction Id')

        return value
    
    @field_validator('rating')
    @classmethod
    def interact_valid(cls,value : int):
        if value is None:
            return value
        if value < 1 or value > 5 :
            raise ValueError('Inavlid Rating Points')
        return value
    
            

