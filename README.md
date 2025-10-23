# Sprint 5 Practice Assignment: Enabling Intelligent Routing for the Travel & Trip Planner Agent

## Project Context

In Sprint 4, your **Travel & Trip Planner Agent** learned how to use tools — it could fetch your current location and provide destination details from an internal database.  
However, the agent still followed a **fixed, one-size-fits-all process**. Every query — whether it was feedback, a booking request, or a cancellation — was handled in the same linear way.

In real-world applications, intelligent systems must **adapt their workflow** based on what the user says and how urgent it sounds.  
For example:  
- “Your booking system is not working.” → needs **immediate, high-urgency** handling  
- “Book a 3-day trip to Bali.” → should trigger a **booking workflow**  
- “Cancel my hotel reservation in Paris.” → should follow a **cancellation path**  
- “What’s the best time to visit Japan?” → can be answered through a **general knowledge flow**

In this sprint, you will make your agent **smarter and context-aware** using **LangChain Expression Language (LCEL)**.  
You’ll learn how to:  
1. Build **multi-step LLM pipelines** that analyze customer feedback and decide on the right response strategy.  
2. Implement **router chains** that conditionally direct travel queries — such as booking, cancellation, or general inquiries — to different response flows.  

By the end of this sprint, your Travel & Trip Planner agent will no longer treat every query the same way.  
It will **analyze, decide, and respond intelligently** — just like a real travel support agent.

---

## Problem Statement

You will create a **FastAPI-based AI workflow** using LCEL with two major tasks.  
Each task will build upon the previous one and demonstrate how to create **multi-step and conditional pipelines** using the `|` (pipe) operator and `RunnableBranch`.

---

### Task 1 — Build a Multi-Step LCEL Chain for Travel Feedback Analysis

#### Goal
Create a **multi-step LCEL pipeline** that analyzes customer feedback, identifies its sentiment and urgency, and generates a professional response strategy.

#### Requirements

1. Create a file named `feedback_chain.py`.
2. Initialize the LLM using your Gemini API key with `ChatOpenAI`.
3. Implement the following workflow using the pipe (`|`) syntax:
   - Step 1: A prompt that classifies the **sentiment** of the feedback as POSITIVE, NEGATIVE, or NEUTRAL.
   - Step 2: A **RunnableLambda** that assigns **urgency level** based on sentiment:
     - NEGATIVE → HIGH  
     - NEUTRAL → MEDIUM  
     - POSITIVE → LOW  
   - Step 3: Another prompt that asks the LLM to generate a **response strategy** based on sentiment and urgency.
4. Combine all components into one LCEL chain:
   ```python
   feedback_chain = sentiment_prompt | llm | StrOutputParser() | urgency_classifier | strategy_prompt | llm | StrOutputParser()
   ```
5. Create a FastAPI endpoint `/analyze_feedback` that:
   - Accepts a POST request with JSON input:
     ```json
     {
       "feedback": "Your booking system crashed twice while planning my trip!"
     }
     ```
   - Invokes the `feedback_chain` and returns the sentiment, urgency, and strategy.


#### Debug Tips
- Make sure your custom function returns a dictionary, not a string.
- If you see a KeyError, check that the variable names in your prompts match your dictionary keys.
- Print inside `RunnableLambda` to verify data flow.

---

### Task 2 — Intelligent Routing for Booking, Cancellation, and General Travel Queries

#### Goal
You will build a router chain that classifies user queries into three categories — **BOOKING, CANCELLATION, or GENERAL** — and generates a response suited to each case.

This helps your Travel & Trip Planner Bot respond appropriately to different types of customer queries.

#### Requirements

1. Create a file `travel_router.py`.

2. Initialize the LLM using your Gemini API key with `ChatOpenAI`.

3. Create an **Intent classification chain**:

    - **BOOKING**: User wants to book or reserve travel (flight, hotel, trip, etc.)

    - **CANCELLATION**: User wants to cancel or change a booking

    - **GENERAL**: Any other travel-related question or feedback
      *Respond with only one word: BOOKING, CANCELLATION, or GENERAL.*

4. Create three separate response chains:

    - **Booking Chain**: Confirm booking details or guide the user on next steps.

    - **Cancellation Chain**: Apologize, confirm cancellation, and mention refund info.

    - **General Chain**: Give helpful travel answers or suggestions.

5. Create **condition functions** for the first two chains:
```python
   def is_booking_query(data: dict) -> bool:
      return data.get("intent", "").strip().upper() == "BOOKING"

   def is_cancellation_query(data: dict) -> bool:
      return data.get("intent", "").strip().upper() == "CANCELLATION"

```
6. Build a **RunnableBranch router**:

    - (is_booking_query, booking_chain)

    - (is_cancellation_query, cancellation_chain)

    - default → general_chain

7. Prepare input for routing using a helper function (RunnableLambda) that calls the classification chain

8. Expose a FastAPI endpoint `/route_query` for testing.

#### Example Queries

| User Query | Expected Route | Example Response |
|--------|----------------|----------------|
| “Book me a 3-day trip to Bali.” | BOOKING | `“Your Bali trip booking is being processed. Please confirm travel dates and accommodation preferences.” |
|“Book me a 3-day trip to Bali.” | CANCELATION | “I’ve initiated your Paris hotel cancellation. A refund will be processed within 5 business days.” |
| “When is the best time to visit Japan?” | GENERAL | “The best months to visit Japan are March to May during cherry blossom season.” |

---

## Project Setup

1. Create two files:
   - `feedback_chain.py` → Task 1  
   - `travel_router.py` → Task 2  


---

## Configuration

Create a `.env` file in your project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL_NAME=gemini-2.0-flash

```

---

## Run the feedback_chain.py file

```bash
uv run uvicorn feedback_chain:app --host 0.0.0.0 --port 8000 --reload
```
## Run the travel_router.py file

```bash
uv run uvicorn travel_router:app --host 0.0.0.0 --port 8000 --reload
```

Visit **http://localhost:8000/docs** to interact with your endpoints through Swagger UI.

---

## Testing the API

| Endpoint | Description | Example Input |
|-----------|--------------|----------------|
| `/analyze_feedback` | Analyzes travel feedback | “Your website is slow while searching destinations.” |
| `/route_query` | Classifies and routes trip queries | "Book me a 3-day trip to Bali." |

---

## Expected Learning Outcomes

By completing this sprint, you will learn how to:
- Create **multi-step LCEL chains** combining prompts, LLMs, and custom Python logic.  
- Use **RunnableBranch** for intelligent query routing.  
- Integrate **tool calling and decision-making** within LCEL workflows.  
- Build modular, testable AI pipelines with **FastAPI** endpoints.
