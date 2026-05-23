# stateful_trip_agent.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.schema.output_parser import StrOutputParser
from pydantic import BaseModel
import uuid
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import logging
from pathlib import Path
# -------------------------------
# Environment Setup
# -------------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file.")

# -------------------------------
# Initialize FastAPI App
# -------------------------------
app = FastAPI(title="Stateful Travel & Trip Planner Agent")



# Task1 : Enable CORS for secure frontend-backend communication on localhost.
origins = [
    'http://localhost:5173',
    'http://localhost:3000'  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# LLM Setup
# -------------------------------
llm = ChatOpenAI(
    model=model_name, 
    api_key=api_key, 
    base_url=base_url, 
    streaming=True)

# -------------------------------
# Prompt Template with Memory
# -------------------------------
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful travel assistant. Remember the user's trip details, activities, and preferences during this session."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}")
])

# -------------------------------
# Session Memory Store
# -------------------------------
store = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

# -------------------------------
# Core LCEL Chain
# -------------------------------
core_chain = prompt | llm | StrOutputParser()

# -------------------------------
# Wrap with Session-Based Memory
# -------------------------------
stateful_chain = RunnableWithMessageHistory(
    runnable=core_chain,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)

def setup_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(log_dir / "AI_MODELS.log")

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%d-%m-%Y %H:%M:%S",
        )

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

log = setup_logger()

# -------------------------------
# FastAPI Endpoint
# -------------------------------

class ChatInput(BaseModel):
    input: str
    session_id: str

@app.get("/new-session")
def new_session():
    """Generate a new chat session ID."""
    return {"session_id": str(uuid.uuid4())}

@app.post("/chat")
async def chat(payload: ChatInput):
    """
    Stateful chat endpoint that remembers context per session.
    Streams the model's response token by token.
    """
    config = {"configurable": {"session_id": payload.session_id}}

    async def event_generator():
        try:
            # Use .astream() for non-blocking streaming in an async context
            log.debug(f"Started streaming..")
            async for chunk in stateful_chain.astream({"input": payload.input}, config=config):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            # Log the full error for debugging
            log.error(f"Error during stream: {e}")
            print(f"Error during stream: {e}")
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# -------------------------------
# Run App
# -------------------------------
if __name__ == "__main__":
    
    uvicorn.run("stateful_trip_agent:app", host="0.0.0.0", port=8000)
