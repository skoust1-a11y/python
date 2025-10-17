# Sprint 2 Assignment: Building the Core of the Travel Suggestion Agent (FastAPI Edition)

## Project Context
You are the lead developer for the new **Travel & Trip Planner Agent**. Your first major goal is to build the core "suggestion engine." This engine will be responsible for all interactions with the Large Language Model (LLM).  

In this sprint, you will build this engine using **LangChain** and **FastAPI** in three stages:
1. Create a baseline synchronous version.
2. Add versatility with factual and creative output modes.
3. Implement an asynchronous pattern for LLM calls — a critical step for developing fast, modern APIs.

---

## Problem Statement
Create a uv project using `uv init travel_agent` which implements a **FastAPI backend** capable of generating dynamic travel suggestions using the ChatOpenAI API via LangChain.

Your API must expose **three endpoints**, one for each task. Each endpoint should accept **user input** via a JSON request body and return the LLM-generated output as a structured JSON response


### Task 1: Baseline Itinerary Generator (Synchronous)
The goal of this task is to build the most basic version of the travel suggestion engine that synchronously invokes the LLM.

#### Requirements
1. **Environment Setup**
   - Load your API key securely from a `.env` file using `python-dotenv`.
   - Use the key `GEMINI_API_KEY` for this task.
2. **LLM Instantiation**
   - Import `ChatOpenAI` from `langchain_openai` and create an instance of the `"GEMINI_MODEL_NAME"` model.
   - Configure it with `max_retries=2` for reliability.
3. **API Endpoint**
   - Create a FastAPI endpoint `/task1` that accepts user inputs:
     - `destination` (e.g., "Paris")
     - `theme` (e.g., "museums and parks")
     - `days` (e.g., `4`)
   - Example prompt:
     > “Suggest a 4-day itinerary for a family trip to Paris, focusing on museums and parks.”
4. **Invocation**
   - Use the `.invoke()` method to call the LLM with the constructed prompt.
5. **Output**
   - Return a JSON response containing the generated itinerary under the heading:  
     `--- Task 1: Baseline Itinerary ---`.

---

### Task 2: Adding Versatility with Factual & Creative Modes
A great travel agent should adapt to user preferences — sometimes users want quick facts, other times creative inspiration. In this task, you’ll add two distinct response styles controlled by LLM hyperparameters.

#### Requirements
1. **Factual Mode**
   - Create a FastAPI POST endpoint `/task2`.
   - Accept a JSON body with a key `factual_prompt`.
   - Instantiate a `ChatOpenAI` model with:
     - `temperature=0.1` (for deterministic answers)
     - `max_tokens=100` (for concise output)
   - Use `.invoke()` to generate the response.
   - Return it under the heading `--- Task 2: Factual Suggestion ---`.

2. **Creative Mode**
   - In the same endpoint, accept another key `creative_prompt`.
   - Instantiate a separate `ChatOpenAI` model with:
     - `temperature=0.9` (for creative diversity)
   - Use `.invoke()` to generate the response.
   - Return it under the heading `--- Task 2: Creative Suggestion ---`.

3. **Output**
   - The endpoint should return a combined JSON response showing both factual and creative outputs.

---

### Task 3: Learning the Asynchronous API
Modern applications require responsive APIs. Instead of blocking while waiting for LLM responses, asynchronous calls allow multiple operations to run concurrently.  
In this task, you’ll implement asynchronous LLM invocation using LangChain’s `.ainvoke()` method and Python’s `async`/`await` syntax.

#### Requirements
1. **Setup**
   - Import `asyncio`.
   - Instantiate a single reusable `ChatOpenAI` model with `temperature=0.5`.
2. **FastAPI Endpoint**
   - Create a GET endpoint `/task3` that accepts a query parameter:
     - `question` (e.g., "What is the best way to get from Narita Airport to downtown Tokyo?")
3. **Async Function**
   - Define an asynchronous function such as:
     ```python
     async def generate_async_suggestion(prompt: str):
         response = await llm.ainvoke(prompt)
         return response.content
     ```
4. **Execution**
   - Call the async function within the FastAPI endpoint using `asyncio.run`.
5. **Output**
   - Return a JSON response under the heading `--- Task 3: Asynchronous Suggestion ---`.

---

## Expected Outcome
The three functional endpoints:
- `/task1` → Generates a travel itinerary (synchronous)
- `/task2` → Provides factual and creative travel suggestions (synchronous, two modes)
- `/task3` → Generates an asynchronous travel suggestion (non-blocking)

Each endpoint should accept **user input** and return **structured JSON responses** containing:
- The user’s prompt
- The corresponding LLM-generated output
- A clear task heading (for readability)

---
## Setup Instructions

1. **Install Dependencies**
   ```bash
   uv sync
   ```

2. **Environment Configuration**
   - Create a `.env` file with your Google Gemini API key:
     ```
     GEMINI_API_KEY=your_api_key_here
     GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
     GEMINI_MODEL_NAME=gemini-2.0-flash
     ```

3. **Run the FastAPI Server**
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Test the API**
   - Open your browser to `http://localhost:8000/docs` for interactive API documentation