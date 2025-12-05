## Project Context

You are the lead developer for the new **Travel & Trip Planner Agent**. Your first major goal is to build the core "suggestion engine" — the component responsible for all interactions with the Large Language Model (LLM).  

In this practice, you will build this engine using **LangChain** and **FastAPI**. You'll start with a baseline synchronous version, then add versatility with different output modes, and finally implement asynchronous patterns for modern, responsive APIs.

---

## Problem Statement

Design and implement the core suggestion engine for your **Travel & Trip Planner Agent** using **LangChain** and **FastAPI**.  
You will complete **three main tasks**:

---

### **Task 1 — Baseline Itinerary Generator (Synchronous)**

#### Goal  
Build the foundational version of the travel suggestion engine that synchronously invokes the LLM to generate travel itineraries.

#### Requirements  
1. Set up your environment file with gemini key.

2. **LLM Instantiation** — Import your LLM class (e.g., `ChatOpenAI`) and instantiate it with your chosen model name and reliability parameters (e.g., `max_retries=2`).

3. **API Endpoint**
   - Create a FastAPI POST endpoint `/task1` that accepts user inputs:
     - `destination` (e.g., "Paris")
     - `theme` (e.g., "museums and parks")
     - `days` (e.g., `4`)
   - Construct a prompt from these inputs (e.g., "Suggest a 4-day itinerary for a family trip to Paris, focusing on museums and parks.").

4. **Invocation**
   - Use the appropriate method to call the LLM with the constructed prompt.

5. **Output**
   - Return a JSON response containing the generated itinerary.

---

### **Task 2 — Adding Versatility with Factual & Creative Modes**

#### Goal  
Enhance the travel agent to adapt to different user preferences by providing both factual and creative response styles controlled by LLM hyperparameters.

#### Requirements  
1. **Factual Mode**
   - In the FastAPI POST endpoint `/task2`, accept a JSON body with a key (such as `factual_prompt`).
   - Instantiate a language model with low temperature (for more deterministic responses) and a limit on maximum output tokens (for concise output).
   - Use the model's method to generate the response.
   - Return the output in JSON format.

2. **Creative Mode**
   - In the same endpoint, accept another key for the creative input (e.g., `creative_prompt`).
   - Instantiate a separate language model with a higher temperature value (e.g., `temperature=0.9` for more creative outputs).
   - Use the model's appropriate method to generate the creative response.
   - Return the creative response in the output with a clear heading.

3. **Output**
   - The endpoint should return a combined JSON response showing both factual and creative outputs.

---

### **Task 3 — Learning the Asynchronous API**

#### Goal  
Implement asynchronous LLM invocation to enable non-blocking, concurrent operations for responsive APIs.

#### Requirements  
1. **Setup**
   - Import an asynchronous framework (e.g., `asyncio`).
   - Instantiate a single reusable language model instance with a moderate temperature value.

2. **FastAPI Endpoint**
   - Create a GET endpoint `/task3` that accepts a query parameter: `question` (e.g., "Ask any question relevant to your use case.")

3. **Async Function**
   - Define an asynchronous function that performs an async operation and returns the result.

4. **Execution**
   - Ensure the async function is properly called within the FastAPI endpoint using an appropriate method for asynchronous execution.

5. **Output**
   - Return a JSON response.
---

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. Environment variables are correctly loaded from `.env` file.
2. LLM models are properly instantiated with correct configuration parameters.
3. FastAPI endpoints correctly accept user input and return structured JSON responses.
4. Task 1 endpoint generates synchronous travel itineraries based on user inputs.
5. Task 2 endpoint provides both factual and creative responses with appropriate temperature settings.
6. Task 3 endpoint implements asynchronous LLM invocation correctly.

