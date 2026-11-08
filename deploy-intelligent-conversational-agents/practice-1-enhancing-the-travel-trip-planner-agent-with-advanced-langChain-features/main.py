"""
Sprint 3 Solution — Travel & Trip Planner Agent
LangChain + FastAPI + ChatOpenAI (via langchain_openai)

Implements:
  • Task 1: Fetch Prompt from Langfuse
  • Task 2: Few-Shot Prompting with ChatPromptTemplate.from_messages()
  • Task 3: Structured Output with PydanticOutputParser
"""

import os
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException,Depends
from pydantic import BaseModel, Field, ValidationError
from langchain_openai import ChatOpenAI
from langfuse import Langfuse
from langchain_core.messages import HumanMessage,SystemMessage,AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException,LangChainException


# LangChain imports


# -------------------------------------------------------------------
# Load environment
# -------------------------------------------------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
if not GEMINI_API_KEY:
    raise RuntimeError("Please set GEMINI_API_KEY in your .env file.")

# -------------------------------------------------------------------
# Initialize FastAPI app
# -------------------------------------------------------------------
app = FastAPI(title="Travel Planner Advanced - Sprint 3")
#-------------------------------------------------------------------
# Initialize the Langfuse client using environment variables for public key, secret key, and host URL
#-------------------------------------------------------------------
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")

if not LANGFUSE_BASE_URL:
    raise ValueError('The LangFuse Base Url Not Found in .env file')
if not LANGFUSE_PUBLIC_KEY:
    raise ValueError('The LangFuse Public Key Not Found in .env file')
if not LANGFUSE_SECRET_KEY:
    raise ValueError('The LangFuse Secre Key Not Found in .env file')
    


langfuse_client = Langfuse(
    base_url=LANGFUSE_BASE_URL,
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY
)

# -------------------------------------------------------------------
# Helper: initialize LLM client
# -------------------------------------------------------------------
llm= ChatOpenAI(
        model=GEMINI_MODEL_NAME,
        api_key=GEMINI_API_KEY,
        base_url=GEMINI_BASE_URL,
        temperature=0.3,
        max_retries=2,
    )

# -------------------------------------------------------------------
# Task 1 — Fetch Prompt from Langfuse
# -------------------------------------------------------------------
#Define a Pydantic model to capture itinerary request details: destination, number of days, and budget
class ItineraryReq(BaseModel):
    destination : str = Field(min_length=2,
        description='Destination Place'
    )
    days : int = Field(gt=0, lt=3,description='Number Of Days')
    budget : float = Field(gt=0,description='The Total Budget')

class ItineraryRes(BaseModel):
    itinerary_response : str
#Implement an async FastAPI route that retrieves a production prompt from Langfuse, replaces placeholders with user 
# data, invokes the LLM, and returns the response, handling errors if the prompt is missing
@app.get('/task1',response_model=ItineraryRes)
async def get_itinerary_res(query : ItineraryReq = Depends()):
    try:
        prompt = langfuse_client.get_prompt(
            name='travel_suggest_prompt',
            label='production'
        )
        if not prompt:
            raise HTTPException(
                status_code=404,
                detail='Prompt Not Found'
            )
        newPrompt = prompt.prompt

        prompt_text = newPrompt.replace('{{days}}',str(query.days))
        prompt_text = prompt_text.replace('{{destination}}',query.destination)
        prompt_text = prompt_text.replace('{{budget}}',str(query.budget))

        messages = [HumanMessage(content=prompt_text)]

        response = await llm.ainvoke(messages)

        result = response.content

        return ItineraryRes(itinerary_response=result)
    
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f'Pydantic Error: {str(e)}')

    except LangChainException as e:
        raise HTTPException(status_code=502, detail=f'LLM Error: {str(e)}')

    except OutputParserException as e:
        raise HTTPException(status_code=500, detail=f'Parsing Error: {str(e)}')

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f'Prompt Placeholder Error: {str(e)}')

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {str(e)}')

# -------------------------------------------------------------------
# Task 2 — Few-Shot Prompting with ChatPromptTemplate.from_messages()
# -------------------------------------------------------------------

#Define a Pydantic model UserQuery to capture the user’s input query for processing

class UserQuery(BaseModel):
    usrQuery : str = Field(description='The Query asked by the Client')
class ResponseTravel(BaseModel):
    travel_res :  str
# Create a POST endpoint /task2 that uses few-shot prompting with ChatPromptTemplate to generate a day-by-day travel itinerary 
# from a user query
@app.post('/task2',response_model=ResponseTravel)
async def task2(qry : UserQuery):
    try:
        chat_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="""
You are a Professional travel planning assistant.

Use the following examples as reference for style only.
Do NOT include previous destinations.

Generate response ONLY for the latest query.
"""),
        HumanMessage(content='User is a solo traveler visting Japan for 5 days'),
        AIMessage(content='Here’s a 5-day Japan itinerary: Day 1-2 Tokyo exploration, Day 3 Mt. Fuji/Hakone, Day 4 Kyoto temples, Day 5 Osaka food and nightlife.'),

        HumanMessage(content='Family of 4 visiting Thailand for 6 days'),
        AIMessage(content='Family-friendly Thailand plan: Bangkok (2 days for temples & safari), Phuket/Krabi (3 days beaches & island tours), final day shopping and relaxation.'),

        HumanMessage(content='Couple with one child visiting Dubai for 4 days'),
        AIMessage(content='Dubai plan: Day 1 Burj Khalifa & Dubai Mall, Day 2 Desert safari, Day 3 Atlantis waterpark, Day 4 Miracle Garden & Global Village.'),

        HumanMessage(content='{chatInput}')])
        formatted_msg = chat_prompt.format_messages(
            chatInput=qry.usrQuery
        )
        resposne = await llm.ainvoke(formatted_msg)

        result = resposne.content

        return ResponseTravel(travel_res=result)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f'Pydantic Error: {str(e)}')

    except LangChainException as e:
        raise HTTPException(status_code=502, detail=f'LLM Error: {str(e)}')

    except OutputParserException as e:
        raise HTTPException(status_code=500, detail=f'Parsing Error: {str(e)}')

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f'Prompt Placeholder Error: {str(e)}')

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {str(e)}')
# -------------------------------------------------------------------
# Task 3 — Structured Output Parsing (PydanticOutputParser)
# -------------------------------------------------------------------
# Define Pydantic schema for validated output
class TripPlan(BaseModel):
    destination: str = Field( 
        min_length=1,
        description="Travel destination")
    days: int = Field( 
        ge=1,
        le=30,
        description="Number of days for the trip")
    estimated_cost: str = Field( 
        min_length=1,
        description="Estimated total cost for the trip")
    highlights: List[str] = Field( 
        min_items=1,
        max_items=10,
        description="Top highlights of the destination")

class TripPlanRequest(BaseModel):
    destination: str 
    days: int 
    budget: int 

#Implement an async FastAPI route that formats a prompt with ChatPromptTemplate, invokes the LLM, 
# parses the response with PydanticOutputParser, and handles validation or general errors gracefully.
@app.post('/task3',response_model=TripPlan)
async def task3(req : TripPlanRequest):
    try:
        parser = PydanticOutputParser(pydantic_object=TripPlan)
        format_instructions = parser.get_format_instructions()

        prompt = ChatPromptTemplate.from_messages([
            ('system','You are a expert travel planner.'),
            ('human',"Suggest a {days}-day itinerary for {destination} under a budget of ${budget}.{format_instructions}.Do NOT ask questions.Do NOT explain anything.Return ONLY valid JSON.")
        ])
        # prompt = 'You are a expert travel planner.Suggest a {{days}}-day itinerary for {{destination}} under a budget of ${{budget}}.Include Top attraction Places and Local Food Recommendations.'
        if not prompt:
            raise HTTPException(
                status_code=404,
                detail='Prompt Not Found'
            )
        prompt_text = prompt.format_messages(
            days=req.days,
            destination = req.destination,
            budget = req.budget,
            format_instructions=format_instructions
        )

        # prompt_text = newPrompt.replace('{{days}}',str(req.days))
        # prompt_text = prompt_text.replace('{{destination}}',req.destination)
        # prompt_text = prompt_text.replace('{{budget}}',str(req.budget))

        response = await llm.ainvoke(prompt_text)

        parsed_output = parser.parse(response.content)

        return parsed_output.dict()
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f'Pydantic Error: {str(e)}')

    except LangChainException as e:
        raise HTTPException(status_code=502, detail=f'LLM Error: {str(e)}')

    except OutputParserException as e:
        raise HTTPException(status_code=500, detail=f'Parsing Error: {str(e)}')

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f'Prompt Placeholder Error: {str(e)}')

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {str(e)}')
        


    

# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
