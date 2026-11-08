# trip_memory_prompt.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage
from typing import List
# -------------------------------
# Environment Setup
# -------------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is required. Please set it in your .env file.") 

# -------------------------------
# Initialize FastAPI App
# -------------------------------
app = FastAPI(title="Memory-Aware Prompt Demo")

# -------------------------------
# Initialize LLM
# -------------------------------
llm = ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url)

# -------------------------------
# Memory-Aware Prompt Template
# -------------------------------
stateful_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful travel assistant. You remember the user's travel plans during the conversation."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}")
])
#-------------------------------
# Sample Chat History 
#------------------------------
# Create a sample chat_history list containing alternating human and AI messages to simulate a 
# conversation, which can be used to test prompts or memory integration.
conversation_history: List = [
    HumanMessage(content="What is the best city to visit in india."),
    AIMessage(content="Hyderabd would be the bcest city to visit in India.")
]

# -------------------------------
# Endpoint
# -------------------------------

#Create a FastAPI /trip_chat endpoint that demonstrates memory-aware prompts by appending user input to a manual chat_history, formatting the prompt with MessagesPlaceholder, 
# invoking the LLM, and returning the user input and agent’s response.
@app.get("/stateful")
async def stateful_endpoint(input: str):
    # Add the current user input to history
    conversation_history.append(HumanMessage(content=input))
    
    # Format messages with the updated history
    formatted_messages = stateful_prompt.format_messages(
        input=input,
        chat_history=conversation_history  # provide the updated history
    )
    
    # Get AI response
    response = llm.invoke(formatted_messages)
    
    # Add the AI response to history
    conversation_history.append(AIMessage(content=response.content))
    
    return {
        "user_input":input,
        "response": response.content
        }


# -------------------------------
# Run App
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("trip_memory_prompt:app", host="0.0.0.0", port=8000)
