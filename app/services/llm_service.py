from ..config import settings


open_ai_key = settings.get_env("OPENAI_API_KEY")
gemini_key = settings.get_env("GEMINI_API_KEY")
#Maintain all base url , model type , api key in .env and access them here using settings.get_env() method. This way we can easily switch between different LLMs by just changing the .env file without modifying the codebase.
def call_gemini_llm(prompt: str):
    # Placeholder for LLM interaction
    return "AI-generated response"


def call_gemma_llm(prompt: str):
    # Placeholder for LLM interaction
    return "AI-generated response"