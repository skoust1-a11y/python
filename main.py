import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from router import assess_complexity

load_dotenv()

# ---------- Configuration & Clients ----------
# LiteLLM already handles the model routing via config
LITELLM_GATEWAY_URL = "http://localhost:4000/v1"

# TODO: Initialize the OpenAI client pointing to the LiteLLM Gateway
client = None 

app = FastAPI(title="Support Gateway Router")

# ---------- Schema ----------
# TODO: Define the Pydantic model for the incoming request (TicketRequest)
# It should ONLY take a 'description' field.
class TicketRequest(BaseModel):
    pass

# ---------- Core Logic ----------

@app.post("/resolve")
async def resolve_ticket(ticket: TicketRequest):
    """
    TASK 2: Implement the Gateway Router Logic.
    
    Steps:
    1. Call the 'assess_complexity' function from router.py.
    2. Determine which model tier to use:
       - complexity == "complex" -> "complex-agent"
       - complexity == "simple"  -> "simple-agent"
    3. Call the LiteLLM Gateway via the OpenAI client.
    4. Return the resolution and the routing metadata.
    """
    
    # TODO: Step 1 & 2 - Heuristic Assessment & Model Selection
    
    try:
        # TODO: Step 3 - Call GateWay (LiteLLM)
        # Use a system message: "You are a professional customer support assistant. Provide helpful and concise resolutions."
        
       
        
        # TODO: Step 4 - Return the response
        return ""
            
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gateway Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
