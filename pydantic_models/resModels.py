from pydantic import BaseModel


class SuggestionResponse(BaseModel):
    factual_response : str
    creative_response : str

class LLMResponse(BaseModel):
    response : str

class AsyncSuggestionResponse(BaseModel):
    response : str
    execution_type : str = 'async'