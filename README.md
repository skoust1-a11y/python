## Project Context

You are continuing as the lead developer of the **Travel & Trip Planner Agent**, an AI-powered system that helps users plan trips based on their preferences, budget, and destination.  

In earlier practice, you built the core suggestion engine and learned how to make synchronous and asynchronous LLM calls using **LangChain**, **Gemini**, and **FastAPI**.  

In this practice, you will **enhance this engine** by integrating advanced LangChain capabilities such as **prompt templates**, **few-shot prompting**, and **structured output parsing**. By the end, you will have a robust and intelligent trip planner that can produce structured, contextual, and reliable travel recommendations.

---

## Problem Statement

Enhance your **Travel & Trip Planner Agent** by integrating advanced LangChain features for dynamic prompt management, personalized recommendations, and structured output generation.  
You will complete **three main tasks**:

---

### **Task 1 — Fetch Dynamic Prompt from Langfuse**

#### Goal  
Demonstrate dynamic prompt generation from an external source (Langfuse) instead of local templates, creating prompts that adapt to user inputs such as destination, duration, and budget.

#### Requirements  
1. **Langfuse Connection**
   - Connect to Langfuse using your API credentials.

2. **Prompt Template Setup**
   - Fetch a pre-defined prompt template from Langfuse (e.g., `travel_itinerary`).
   - Configure the prompt with appropriate settings (e.g., label: `production`, temperature: `0.7`).
   - Define a prompt template in Langfuse with placeholders such as `{destination}`, `{days}`, and `{budget}`.

3. **API Endpoint**
   - Create a FastAPI endpoint `/task1` that accepts query parameters: `destination`, `days`, and `budget`.
   - Fetch the template from Langfuse and fill the placeholders with user inputs.
   - Use the fetched template to generate the LLM prompt.

4. **LLM Invocation**
   - Invoke the LLM (Gemini) with the generated prompt and return the itinerary response.

---

### **Task 2 — Few-Shot Prompting for Personalized Recommendations**

#### Goal  
Teach the model to produce better recommendations by using few-shot examples to guide the model's output style and context.

#### Requirements  
1. **Prompt Template Setup**
   - Use `ChatPromptTemplate` to define a system message and example interactions.
   - Include examples that demonstrate different travel scenarios (e.g., solo traveler, couple, family).
   - Show how each example should be formatted in the response.

2. **API Endpoint**
   - Create a POST endpoint `/task2` that accepts a user query.

3. **Few-Shot Prompt Construction**
   - Combine the examples and user input into a single few-shot prompt.

4. **LLM Invocation**
   - Invoke the LLM (Gemini) with the few-shot prompt and return the personalized itinerary.

---

### **Task 3 — Structured Output Parsing for Trip Data**

#### Goal  
Ensure the model outputs structured JSON that can be easily stored or visualized on the frontend by using Pydantic models and LangChain's output parsers.

#### Requirements  
1. **Pydantic Schema Definition**
   - Define a Pydantic model (e.g., `TripPlan`) with fields such as:
     - `destination` (str)
     - `days` (int)
     - `estimated_cost` (str)
     - `highlights` (list of strings)

2. **Output Parser Setup**
   - Use LangChain's `PydanticOutputParser` to enforce structured output from the LLM.

3. **API Endpoint**
   - Create an endpoint `/task3` that accepts user input (`destination`, `days`, `budget`).

4. **LLM Invocation and Parsing**
   - Format the prompt with the output parser instructions.
   - Invoke the LLM and parse the response using the PydanticOutputParser.

5. **Response**
   - Return a JSON response following your `TripPlan` schema.

---

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. Langfuse connection is properly configured and prompts are successfully fetched from the external source.
2. Task 1 endpoint correctly fills template placeholders and generates dynamic prompts based on user inputs.
3. Task 2 endpoint implements few-shot prompting with appropriate examples that guide the model's output style.
4. Task 3 endpoint uses PydanticOutputParser to enforce structured output validation.
5. All endpoints correctly invoke the LLM and return appropriate responses.
6. Structured output from Task 3 follows the defined Pydantic schema and validates correctly.

