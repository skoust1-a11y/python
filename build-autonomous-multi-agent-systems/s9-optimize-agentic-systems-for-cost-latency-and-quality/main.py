"""
Customer Support Ticket Optimization System - FastAPI Gateway Router.

LiteLLM Gateway Configuration (litellm_config.yaml):
- simple-agent:  ollama/llama3.2  (http://localhost:11434) - Local, 0-cost, low latency
- complex-agent: azure/gpt-4o-mini (os.environ/AZURE_OPENAI_API_KEY, os.environ/AZURE_OPENAI_ENDPOINT) - Cloud reasoning
"""
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from openai import OpenAI
from dotenv import load_dotenv
from router import assess_complexity

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# ---------- Configuration & Clients ----------
LITELLM_GATEWAY_URL = "http://localhost:4000/v1"

# Full LiteLLM gateway configuration content as defined in litellm_config.yaml:
LITELLM_CONFIG_YAML = """
model_list:
  # Simple tier -> local Ollama model (zero cost, low latency)
  - model_name: simple-agent
    litellm_params:
      model: ollama/llama3.2
      api_base: http://localhost:11434

  # Complex tier -> Azure OpenAI (higher reasoning capability)
  - model_name: complex-agent
    litellm_params:
      model: azure/gpt-4o-mini
      api_key: os.environ/AZURE_OPENAI_API_KEY
      api_base: os.environ/AZURE_OPENAI_ENDPOINT
      api_version: os.environ/AZURE_OPENAI_API_VERSION
"""

client = OpenAI(
    base_url=LITELLM_GATEWAY_URL,
    api_key="dummy-key",
)

app = FastAPI(title="Support Gateway Router")

SYSTEM_PROMPT = (
    "You are a professional customer support assistant. "
    "Provide helpful and concise resolutions."
)

# Maps the router's assessment to the model tier defined in litellm_config.yaml
MODEL_MAP = {
    "simple": "simple-agent",    # -> ollama/llama3.2 (local, low cost/latency)
    "complex": "complex-agent",  # -> azure/gpt-4o-mini (cloud, high reasoning)
}


# ---------- Schema ----------
class TicketRequest(BaseModel):
    description: str = Field(..., min_length=1, description="Support ticket description")

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("description must not be empty or whitespace only")
        return cleaned


class TicketResponse(BaseModel):
    query: str = Field(..., description="Original customer query or ticket description")
    complexity_assessment: str = Field(..., description="Complexity assessment outcome ('simple' or 'complex')")
    routed_model_tier: str = Field(..., description="Model tier selected for routing ('simple-agent' or 'complex-agent')")
    resolution: str = Field(..., description="Generated resolution response from the model tier")


# ---------- Core Logic ----------
@app.post("/resolve", response_model=TicketResponse)
async def resolve_ticket(ticket: TicketRequest):
    """Route a support ticket to the appropriate model tier via the LiteLLM gateway."""
    # Step 1 & 2 - Heuristic assessment & model tier selection
    complexity = assess_complexity(ticket.description)
    model_tier = MODEL_MAP[complexity]
    logger.info(f"Ticket assessed as '{complexity}', routing to tier: '{model_tier}'")

    try:
        # Step 3 - Call the LiteLLM gateway
        response = client.chat.completions.create(
            model=model_tier,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": ticket.description},
            ],
        )

        # Step 4 - Return resolution plus routing metadata
        return {
            "query": ticket.description,
            "complexity_assessment": complexity,
            "routed_model_tier": model_tier,
            "resolution": response.choices[0].message.content,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gateway Error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
