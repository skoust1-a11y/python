from pydantic import BaseModel,field_validator,Field

class UserInput(BaseModel):
    text: str = Field(...,description='The Prompt given by Patient')
    user_id: str =Field(...,description='The User_ID')

    @field_validator('text')
    @classmethod
    def text_valid(cls,value : str):
        if len(value)  == 0:
            raise ValueError('Empty Prompt,Plz Give a Valid Prompt')
        return value
    
    @field_validator('user_id')
    @classmethod
    def user_valid(cls,value : str):
        if len(value) == 0:
            raise ValueError('Inavlid User Id')
        return value
