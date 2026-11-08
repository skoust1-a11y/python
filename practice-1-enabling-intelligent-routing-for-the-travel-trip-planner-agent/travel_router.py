import os
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
# from langchain_core.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
# from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableBranch
from llmsetup import llm
# Load environment


# Initialize LLM


# -------------------------------
# Step 1: Intent Classification
# -------------------------------
intent_prompt = ChatPromptTemplate.from_messages([
    ("system", "Classify this travel-related query as one of the following:\n"
               "- BOOKING: user wants to book/reserve a trip, hotel, or flight.\n"
               "- CANCELLATION: user wants to cancel or change an existing booking.\n"
               "- GENERAL: user is asking about travel info or suggestions.\n"
               "Respond with only one word: BOOKING, CANCELLATION, or GENERAL."),
    ("user", "{query}")
])
travel_action_chain = intent_prompt | llm | StrOutputParser()

# -------------------------------
# Step 2: Condition Functions
# -------------------------------
def classify_helper_for_booking(input_dict : dict) -> bool:
    classification = input_dict.get("classification","").strip().upper()
    return classification == 'BOOKING'
def classify_helper_for_cancel(input_dict : dict) -> bool:
    classification = input_dict.get("classification","").strip().upper()
    return classification == 'CANCELLATION'

# -------------------------------
# Step 3: Branch Chains
# -------------------------------
booking_prompt = ChatPromptTemplate.from_messages([
    ('system',"You are a Booking Assistant responsible for handling user booking requests.Your job is to:Understand the user's booking intent clearly (e.g., hotel, travel, appointment, service, etc.)Extract key details such as date, time, location, number of people, and preferences Ask for missing information if required before confirming the booking Provide a clear and structured response"),
    ('user',"Original Query: {original_query}")
])
booking_chain = booking_prompt | llm | StrOutputParser()

cancel_prompt = ChatPromptTemplate.from_messages([
    ('system',"You are a Cancellation Assistant that identifies cancellation intent, extracts relevant details, checks completeness, confirms cancellation only when sufficient info is available, explains refund policy if applicable, asks for missing details when needed, and responds concisely and professionally without making assumptions or false confirmations."),
    ('user',"Original Query: {original_query}")
])

cancel_chain = cancel_prompt | llm | StrOutputParser()

general_prompt = ChatPromptTemplate.from_messages([
    ('system',"You are a Travel Assistant that answers general travel inquiries, provides accurate and helpful suggestions on destinations, itineraries, transportation, and tips, asks for clarification when needed, and responds concisely, clearly, and professionally without making assumptions."),
    ('user',"Original Query: {original_query}")
])
general_chain = general_prompt | llm | StrOutputParser()

# -------------------------------
# Step 4: Router
# -------------------------------

router = RunnableBranch(
    (classify_helper_for_booking,booking_chain),
    (classify_helper_for_cancel,cancel_chain),
    general_chain
)

# -------------------------------
# Step 5: Orchestration
# -------------------------------
def prepare_router_input(query: str) -> dict:
    classification = travel_action_chain.invoke({"query":query})
    return {
        'classification':classification,
        'original_query':query
    }
router_deciding_input = RunnableLambda(prepare_router_input)

full_chain = router_deciding_input | router

# -------------------------------
# Step 6: FastAPI Setup
# -------------------------------

app = FastAPI(title="Travel Action Deciding Planner")

class QueryInput(BaseModel):
    query : str

class QueryOutput(BaseModel):
    user_query : str
    response : str

@app.post('/route_query')
def route_query(data : QueryInput):
    try:
        result = full_chain.invoke({"query": data.query})
        return QueryOutput(user_query=data.query,response=result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"The error is: {str(e)}"
        )
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("travel_router:app", host="0.0.0.0", port=8000)
