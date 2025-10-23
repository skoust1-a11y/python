# Sprint 4 Practice Assignment: Equipping the Travel & Trip Planner Bot with Tools and Intelligence

## Project Context
You’ve already built the core travel suggestion engine in previous sprints — it can generate itineraries and structured outputs.  
Now, it’s time to make your **Trip & Travel Agent** smarter by giving it **tools** it can use to fetch information, reason about data, and respond intelligently.

You will:
1. Build an internal tool that uses an LLM to fetch and summarize travel details.  
2. Build an **external tool** that connects to a live API.  
3. Combine them into an **agent** that can decide which tool to use automatically.  

---

## Problem Statement

You will create and test three tasks:

---

### **Task 1 — Create and Test an Internal Tool (`get_destination_info`)**

#### Goal
Create an internal tool that uses the Gemini LLM to fetch and summarize travel-related details for any destination.

#### Requirements
1. Create a file with name `travel_tools.py`
2. Inside this file, import required packages.
3. Load environment variables.
4. Initialize the LLM.
4. Define a function decorated with @tool.
```
@tool
def get_destination_info(destination: str):
    """Fetch travel details for a given destination using Gemini LLM."""
```
5. Inside the function
- Use the LLM to generate a short travel summary.
- Example prompt:
```
prompt = f"Give a short travel guide for {destination}. Include best visiting months, famous attractions, and what the place is known for."
response = llm.invoke(prompt)
return {"destination": destination, "info": response.content}
```
- Handle errors using try–except and return a JSON error message if any issue occurs.
6. In main.py, create a POST API endpoint /tools/internal that:
- Accepts destination as input.
- Calls the tool using:
```
get_destination_info.invoke({"destination": destination})

```
- Returns the result.
7. Test the endpoint through Swagger UI.
Example query:
```
POST /tools/internal
{
    "destination": "Goa"
}
```
Expected: The LLM responds with travel details about Goa (places to visit, best time, etc.)

### **Task 2 — Create and Test an External API Tool — `get_user_location`
#### Goal

The travel bot should also understand the user’s current location to give localized recommendations.
You will create a LangChain tool that fetches the user’s country using the apiip.net geolocation API.

#### Requirements

1. Add your API key to a .env file:
```
APIIP_API_KEY=your_apiip_key_here
```
2. Write a function get_user_location(input:str) decorated with @tool inside `travel_tools.py` file.
3. Inside, use the requests library to call:
``` http://apiip.net/api/check?accessKey=<your_api_key>```

4. Extract and return only:
``` {"ip": "...", "city": "...", "region": "...", "country": "..."}```

5. Handle errors (e.g., missing API key, network issues) with try...except and return JSON error messages.
6. In `main.py` file create a api endpoint with (`/tools/external`) and call 
  get_user_location.invoke({"input": ""})
7. Test the endpoint through swagger. 

### Task 3 — Build an Intelligent Travel Agent
#### Goal
Combine both tools into a single agent that decides which tool to use based on the user query.

#### Requirements

1. In `main.py` import your tools:
from travel_tools import get_destination_info, get_user_info

2. Initialize an LLM (use LangChain OpenAI with Gemini)
3. Combine your tools.
5. Create an Agent Executor using these tools and your LLM.
- Enable verbose=True to view reasoning steps.
6. Create an endpoint (`/ask`) which will accept input from user and invoke the Agent Executor inside it.
6. Test at least three user queries:
- “what are the visiting place near me” → should use get_destination_info
- “What’s the region of my address?” → should use get_country_ip_info
- “Which months are best to visit Bali?” → should use get_destination_info


### Project Setup

- Create a file `travel_tools.py`.
- Where implement first 2 task which are creating tools `get_destination_info` and `get_user_location`.
- Then in `main.py` file call those two tools and create agent_executor.
- create 3 endpoints :
    - '/ask'- Route to interact with the agent.
    - '/tools/internal' - Test internal tool endpoint
    - '/tools/external' - Test external tool

### Run the application
1. Clone or navigate to the project directory:
   ```bash
   cd practice_lo3
   ```

2. Install dependencies using UV:
   ```bash
   uv sync
   ```

   This will automatically:
   - Create a virtual environment
   - Install all dependencies from `pyproject.toml`
   - Set up the project environment

## Configuration

1. Create a `.env` file in the project root:
   ```bash
   touch .env
   ```

2. Add your Google Gemini API key and apiip key to the `.env` file:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   GEMINI_MODEL_NAME=gemini-2.0-flash
   APIIP_API_KEY= your key here
   ```

   To get a Gemini API key:
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account
   - Create a new API key

   To get an APIIP API key:
   - Visit [apiip.net](https://apiip.net/)
   - Sign up for a free account
   - Generate an API key from your dashboard
3. Run tour application:
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

### Testing the API

You can test the endpoint using:
1. **FastAPI Interactive Docs**: Visit `http://localhost:8002/docs` for the automatic interactive API documentation


