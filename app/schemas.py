from pydantic import BaseModel,field_validator,Field

class PromptModel(BaseModel):
    """
    ### Prompt Model

    This model represents the input required to generate a personalized summary.

    ### Fields:
    - **prompt**: A non-empty string provided by the user.

    ### Validation Rules:
    - Must not be `None`
    - Must not be an empty string

    ### Example:
    ```json
    {
        "prompt": "Explain microservices architecture"
    }
    ```
    """

    prompt : str = Field(
        description='User input text for which summary needs to be generated'
    )

    @field_validator('prompt')
    @classmethod
    def prompt(cls,value : str):
        if value is None:
            raise ValueError('Null Prompt..')
        elif value == '':
            raise ValueError('Empty Prompt')
        return value
    
class AnswerModel(BaseModel):
    """
    ### Answer Model

    This model represents the response which includes  a personalized summary.

    """

    status : int
    message : str
    response : str