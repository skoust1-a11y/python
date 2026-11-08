import json
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from travel_tools import get_destination_info, get_user_location
import os
import uvicorn
from travel_tools import get_destination_info,DestinationInput
from pydantic import BaseModel,Field,ValidationError
from langchain_core.exceptions import LangChainException,OutputParserException
import requests
import asyncio
# -------------------------------
# Environment Setup
# -------------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
GEMINI_MODEL_NAME=os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set")

app = FastAPI(title="Travel & Trip Planner Bot", version="4.0")

# -------------------------------
# Initialize LLM (Gemini)
# -------------------------------
model = ChatOpenAI(
    base_url=GEMINI_BASE_URL,
    model=GEMINI_MODEL_NAME,
    api_key=GEMINI_API_KEY,
    temperature=0.3,
)


# -------------------------------
# Step 2: Setup with Tools
# -------------------------------
tools= [get_destination_info,get_user_location]


# -------------------------------
# Step 3: Create Agent
# -------------------------------
prompt= """You are a helpful travel and trip planning assistant.

When users ask about places to visit near them, places near their location, or visiting places in their area:
   - FIRST: Automatically call get_user_location to get the user's city/region
   - THEN: Automatically call get_destination_info with the user's city name (extracted from location) to get travel information
   - DO NOT ask follow-up questions - directly provide the information using both tools

When users ask for a trip plan for a specific destination (e.g., 'Plan a trip to Paris', 'Suggest a trip plan for Mumbai'),
   - ONLY call get_destination_info with the provided destination.
   - Do NOT call get_user_location.
   - Respond with a structured trip plan for that destination.
"""
# Create an Agent using create_agent with the prompt and tools

agent =create_agent(
    model=model,
    tools=tools,
    system_prompt=prompt,
    debug=True
)

# -------------------------------
# ROUTES
# -------------------------------
# Task -1 Test internal tool
# Create an endpoint (`/tools/internal`) and call the get_destination_info tool.
#Implement a FastAPI route that calls the internal LangChain tool get_destination_info, parses its output,
# and handles exceptions with HTTP errors.
@app.post('/tools/internal')
async def call_internal_tool(destination : str):
    try:
        tool_input= DestinationInput(destination=destination)
    except Exception as e:
        raise HTTPException(status_code=400,detail=f"Invalid Input : {str(e)}")
    result_str =  get_destination_info.invoke({"dest" : {"destination" : destination}})
    try:
        data = json.loads(result_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Tool returned invalid JSON format")
    if "error" in data:
        # Map specific tool errors to HTTP Status Codes
        error_msg = data["error"]
        if "Pydantic Error" in error_msg:
            raise HTTPException(status_code=422, detail=error_msg)
        if "LLM Error" in error_msg:
            raise HTTPException(status_code=502, detail=error_msg) # Bad Gateway
        if "Prompt Placeholder Error" in error_msg:
            raise HTTPException(status_code=404,detail=error_msg)
        
        # Default error
        raise HTTPException(status_code=500, detail=error_msg)

    # 5. Success!
    return data

# Task -2 External Tool Test
# Create an endpoint (`/tools/external`) and call the get_user_location tool.
#Implement a FastAPI route that calls the get_user_location LangChain tool, parses the JSON response, 
#and handles any exceptions with HTTP errors
@app.post('/tools/external')
async def call_external_tool():
    '''Invoke the get_user_location to get the location of the user using IP address'''
    try:
        result = get_user_location.invoke({
            "dummy_input": {"query": "fetch_location"}
        })
        data = json.loads(result)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Tool returned invalid JSON format")
    if "error" in data:
        # Map specific tool errors to HTTP Status Codes
        error_msg = data["error"]
        if "Network error " in error_msg:
            raise HTTPException(status_code=424, detail=error_msg)      
        # Default error
        raise HTTPException(status_code=500, detail=error_msg)

    # 5. Success!
    return data



# Task-3 Intelligent Agent Endpoint
# Create an endpoint (`/ask`) which will accept input from user and invoke the agent.
class askQuery(BaseModel):
    query : str = Field(min_length=3)

@app.post("/ask")
async def ask_agent_example1(query: askQuery):
    """
    Example:
      POST /ask {"query": "Suggest a trip plan for mumbai in a neat format"}
      POST /ask {"query": "Where am I located right now?"}
    """
    user_query = query.query
    inputs = {"messages": [{"role": "user", "content": user_query}]}

    try:
        response = agent.invoke(inputs)


        if not response or "messages" not in response:
            raise HTTPException(
                status_code=500,
                detail="Agent returned empty or invalid response structure"
            )


        final_msg = response["messages"][-1].content if response["messages"] else ""

        return {
            "query": user_query,
            "response": final_msg,
            "raw_agent_output": response   # useful for debugging
        }


    # -------------------------------
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Pydantic Validation Error: {str(e)}"
        )


    except OutputParserException as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM Output Parsing Error: {str(e)}"
        )


    except LangChainException as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM/Agent Error: {str(e)}"
        )


    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="External API timeout"
        )

    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Failed to connect to external service"
        )

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=424,
            detail=f"External API error: {str(e)}"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Invalid JSON returned from tool or agent"
        )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Agent execution timed out"
        )


    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Value Error: {str(e)}"
        )

    except TypeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Type Error: {str(e)}"
        )


    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected Server Error: {str(e)}"
        )
    
   



# -------------------------------
# Run Server
# -------------------------------
if __name__ == "__main__":
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
