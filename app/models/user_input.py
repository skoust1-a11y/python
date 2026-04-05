from pydantic import BaseModel

class UserInput(BaseModel):
    text: str
    user_id: str = None