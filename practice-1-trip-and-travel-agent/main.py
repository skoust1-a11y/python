"""
Sprint 2: Building the Core of the Travel Suggestion Agent (FastAPI Edition)
--------------------------------------------------------------
Implements:
1. Baseline itinerary generator (synchronous)
2. Factual & Creative modes with user input
3. Asynchronous travel suggestion with user input

Uses:
- langchain_openai for LLM access
- FastAPI for interactive endpoints
"""

# Import essential libraries, load environment variables, and set up FastAPI with LangChain support
from fastapi import FastAPI,HTTPException,Depends
from langchain_openai import ChatOpenAI
from config import settings
from pydantic_models.reqModels import iternaryReq,promptQues,queryPrompt
from pydantic_models.resModels import SuggestionResponse,LLMResponse,AsyncSuggestionResponse
# -----------------------------------------------------
# Load API credentials from the .env file and set up the FastAPI app with a project title

#Set up the Gemini LLM with API key, model name, and tuning parameters like retries and temperature

def check_err(value):
    if not value:
        raise ValueError('Missing Env Specifications')
    return value

def initialize_gemimi_llm(temperature : int | None = 0.3,
                          max_tokens : int | None = None) -> ChatOpenAI:
    api_key = check_err(settings.require_env('GEMINI_API_KEY',None))
    base_url = check_err(settings.require_env('GEMINI_BASE_URL',None))
    model_name = check_err(settings.require_env('GEMINI_MODEL_NAME',None))

    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        max_retries=2,
        temperature=temperature,
        max_completion_tokens=max_tokens
    )

gemini_llm = initialize_gemimi_llm()    


app =FastAPI()

# -----------------------------------------------------
# Task 1: Baseline Itinerary Generator
# -----------------------------------------------------
#Create Pydantic models to capture user inputs (destination, theme, days) and return the AI-generated response


#Implement a FastAPI POST route that constructs a prompt from the request, calls the LLM, and wraps the output 
# in a Pydantic response model, handling errors gracefully
@app.post('/task1')
def generate_plan(req : iternaryReq) -> LLMResponse:
    try:
        userPrompt = f'Suggest a {req.days}-day itinerary for a family trip to {req.destination} focusing on {req.theme}.'
        planned_result = gemini_llm.invoke(userPrompt)
        generated_itinerary = planned_result.content if hasattr(planned_result,"content") else str(planned_result)
        return LLMResponse(
            response=generated_itinerary
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f'Env Error : {str(e)}',
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=404,
            detail=f'Conenction Timed Out: {str(e)}'
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Internal Error: {str(e)}'
        )


# -----------------------------------------------------
# Task 2: Factual & Creative Modes
# -----------------------------------------------------


# Initialize a factual-focused Gemini model using LangChain with low temperature and token limit for precise responses.
factual_llm = initialize_gemimi_llm(temperature=0.1,max_tokens=100)
#Initialize a creative-focused Gemini model using LangChain with high temperature and larger token limit for more imaginative responses
creative_llm = initialize_gemimi_llm(temperature=0.9,max_tokens=500)

#Create Pydantic models for a prompt-based endpoint, returning factual and creative responses in JSON.

#Implement a FastAPI POST route that constructs prompts from the request, invokes factual_llm and creative_llm, and returns a structured JSON response, handling errors gracefully
@app.post('/task2',response_model=SuggestionResponse)
def generate_both_response(req : promptQues):
    try:
        usr_prmt = f'Answer the following user input clearly and helpfully.User Input:{req.SuggestionRequest}'

        factual_res = factual_llm.invoke(usr_prmt)
        creative_res = creative_llm.invoke(usr_prmt)

        generated_fact_res = factual_res.content if hasattr(factual_res,"content") else str(factual_res)
        generated_creative_res = creative_res.content if hasattr(creative_res,"content") else str(creative_res)

        return SuggestionResponse(
            factual_response=generated_fact_res,
            creative_response=generated_creative_res
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f'Env Error : {str(e)}',
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=404,
            detail=f'Conenction Timed Out: {str(e)}'
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Internal Error: {str(e)}'
        )
    


# -----------------------------------------------------
# Task 3: Asynchronous Suggestion
# -----------------------------------------------------

#Implement an async helper function that invokes the LLM with ainvoke and returns the response content, 
# ensuring exceptions are caught
async def  async_gen_response(prompt : str) -> str:
    try:
        res = await gemini_llm.ainvoke(prompt)
        return res.content if hasattr(res,'content') else str(res)
    except Exception as e:
        raise Exception(f'Error generating async res: {str(e)}')
#Design data models to validate input for asynchronous LLM calls and structure the corresponding response
#Implement a FastAPI GET route that accepts a query parameter via Pydantic validation, constructs a prompt, invokes the async LLM helper,
# and wraps the output in a Pydantic response model with error handling.
@app.get('/task3', response_model=AsyncSuggestionResponse)
async def async_chat(query_request: queryPrompt = Depends()) -> AsyncSuggestionResponse:
    try:
        prompt = f'You are a Helpful Travel Assistant. Please respond to the user message : {query_request.query}'
        response = await async_gen_response(prompt)
        return AsyncSuggestionResponse(
            response=response,
            execution_type='async'
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Internal Error: {str(e)}'
        )
# -----------------------------------------------------
# Local Script Execution
# -----------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
