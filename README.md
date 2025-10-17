# Sprint 3 Practice Assignment: Enhancing the Travel & Trip Planner Agent with Advanced LangChain Features

## Project Context
You are continuing as the lead developer of the **Travel & Trip Planner Agent**, an AI-powered system that helps users plan trips based on their preferences, budget, and destination.  

In **Sprint 2**, you built the core suggestion engine and learned how to make synchronous and asynchronous LLM calls using **LangChain**, **Gemini**, and **FastAPI**.  

In **Sprint 3**, your goal is to **enhance this engine** by integrating advanced LangChain capabilities such as **prompt templates**, **few-shot prompting**, **structured output parsing**.  

By the end of this sprint, you will have a robust and intelligent trip planner that can produce structured, contextual, and reliable travel recommendations.

---

## Problem Statement

You will use **LangChain**, **FastAPI**, and **ChatOpenAI** via `langchain_openai` to demonstrate your understanding.

---

### Task 1: Fetch Dynamic Prompt from Langfuse
You will create a dynamic prompt that adapts to user inputs such as destination, duration, and budget.

#### Requirements
1. Connect to Langfuse using your API key.

2. Fetch a pre-defined prompt template (e.g., travel_itinerary) from Langfuse.
- Name the prompt: `travel_itinerary`
- Set the label to: `production`
- set temperature as 0.7
- Define a prompt template in Langfuse such as:
```
You are an expert travel planner.
Suggest a {days}-day itinerary for {destination} under a budget of ${budget}.
Include top attractions and local food recommendations.
```
3. Fill placeholders in the fetched template: {destination}, {days}, {budget}.
4. Build a FastAPI endpoint /task1 that:
- Accepts query parameters: destination, days, and budget
- Uses the fetched template to generate the LLM prompt
- Invokes the LLM (Gemini) and returns the generated itinerary

**Goal:** Demonstrate dynamic prompt generation from an external source (Langfuse) instead of local templates.

---

### Task 2: Few-Shot Prompting for Personalized Recommendations
You will teach the model to produce better recommendations by showing **examples (few-shots)**.

#### Requirements
1. Use `ChatPromptTemplate` to define a system message and example interactions:
- Example 1: “User is a solo traveler visiting Japan for 5 days.”  
  → “Provide an itinerary focusing on cultural and food experiences.”
- Example 2: “User is a couple visiting Italy for 7 days.”  
  → “Provide a romantic itinerary with scenic and dining experiences.”
2. Accept a new user query through a POST request `/task2`.
3. Combine the examples and user input into a single few-shot prompt.
4. Invoke the LLM (Gemini) and return the personalized itinerary.

**Goal:** Practice few-shot prompting to guide the model’s output style and context.

---

### Task 3: Structured Output Parsing for Trip Data
You will now ensure the model outputs structured JSON that can be easily stored or visualized on the frontend.

#### Requirements
1. Define a **Pydantic model** (e.g., `TripPlan`) with fields such as:
- `destination` (str)
- `days` (int)
- `estimated_cost` (str)
- `highlights` (list of strings)
2. Use LangChain’s `PydanticOutputParser` to enforce structured output.
3. Accept user input (`destination`, `days`, `budget`) via `/task3`.
4. Pass the parsed output to the model using `LLMChain` and `.invoke()`.
5. Return a JSON response following your `TripPlan` schema.

**Goal:** Generate clean, structured, and validated model outputs.

---

## 🎯 Expected Outcome
By completing all four tasks, you will have a FastAPI-based travel planner that demonstrates:

| Concept | Demonstrated Through |
|----------|----------------------|
| Fetching prompt from Langfuse | Task 1 |
| Few-Shot Prompting | Task 2 |
| Output Parsing with Pydantic | Task 3 |

---

## Setup Instructions

1. **Install Dependencies**
   ```bash
   uv sync
   ```

2. **Environment Configuration**
   Create a `.env` file in the project root:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   GEMINI_MODEL_NAME=gemini-2.0-flash
   LANGFUSE_PUBLIC_KEY=your_langfuse_public_key_here
   LANGFUSE_SECRET_KEY=your_langfuse_secret_key_here
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```
   
   **Get your API key:** [Google AI Studio](https://aistudio.google.com/)

3. **Run the FastAPI Server**
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Test the API**
   - Open your browser to `http://localhost:8000/docs` for interactive API documentation
   - Or send POST requests to the retry/basic endpoint

