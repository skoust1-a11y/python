from pydantic import BaseModel,field_validator

class iternaryReq(BaseModel):
    destination : str
    theme : str
    days : int

    @field_validator('destination')
    @classmethod
    def valid_dest(cls,value : str):
        if len(value) == 0:
            raise ValueError('Plz Enter Destination')
        return value
    
    @field_validator('theme')
    @classmethod
    def valid_theme(cls,value : str):
        if len(value) == 0:
            raise ValueError('Plz Enter Theme')
        return value
    
    @field_validator('days')
    @classmethod
    def valid_days(cls,value : int):
        if value <= 0:
            raise ValueError('Plz Enter Valid Number Of Days')
        return value
    

class promptQues(BaseModel):
    SuggestionRequest : str

    @field_validator('SuggestionRequest')
    @classmethod
    def valid_prompt(cls,value : str):
        if len(value) == 0:
            raise ValueError('Plz Enter Valid Question..')
        return value

class queryPrompt(BaseModel):
    query : str

    @field_validator('query')
    @classmethod
    def valid_prompt(cls,value : str):
        if len(value) == 0:
            raise ValueError('Plz Enter Valid Query..')
        return value