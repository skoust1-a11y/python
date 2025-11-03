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

### **Task 2 — Create and Test an External API Tool — `get_user_location`**
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

### **Task 3 — Build an Intelligent Travel Agent**
#### Goal
Combine both tools into a single agent that decides which tool to use based on the user query.

#### Requirements

1. In `main.py` import your tools:
from travel_tools import get_destination_info, get_user_location

2. Initialize a Model (use LangChain OpenAI with Gemini)
3. Combine your tools into a list.
4. Pull the official ReAct prompt from LangChain Hub and create an Agent using `create_react_agent`.
5. Create an endpoint (`/ask`) which will accept input from user and invoke the agent executor.
6. Test at least three user queries:
- "what are the visiting place near me" → should use both get_user_location and get_destination_info
- "What's the region of my address?" → should use get_user_location
- "Which months are best to visit Bali?" → should use get_destination_info


### Project Setup

- Create a file `travel_tools.py`.
- Where implement first 2 task which are creating tools `get_destination_info` and `get_user_location`.
- Then in `main.py` file call those two tools and create agent_executor.
- create 3 endpoints :
    - '/ask'- Route to interact with the agent.
    - '/tools/internal' - Test internal tool endpoint
    - '/tools/external' - Test external tool

### Run the application

1. Navigate to the project directory:

   **For Linux:**
   ```bash
   cd practice-1-trip-and-travel-agent
   ```

   **For Windows:**
   ```cmd
   cd practice-1-trip-and-travel-agent
   ```

2. Install dependencies using UV:

   **For Linux/Windows (Same command):**
   ```bash
   uv sync
   ```

   This will automatically:
   - Create a virtual environment
   - Install all dependencies from `pyproject.toml`
   - Set up the project environment

## Configuration

1. Create a `.env` file in the project root:

   **For Linux:**
   ```bash
   touch .env
   ```

   **For Windows (PowerShell):**
   ```powershell
   New-Item -Path .env -ItemType File
   ```

   **For Windows (CMD):**
   ```cmd
   type nul > .env
   ```

2. Add your Google Gemini API key and apiip key to the `.env` file:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   GEMINI_MODEL_NAME=gemini-2.0-flash
   APIIP_API_KEY=your_apiip_key_here
   ```
   
   **Note**: Make sure there are no spaces around the `=` sign in the `.env` file.

   To get a Gemini API key:
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account
   - Create a new API key

   To get an APIIP API key:
   - Visit [apiip.net](https://apiip.net/)
   - Sign up for a free account
   - Generate an API key from your dashboard
3. Run your application:

   **For Linux/Windows (Same command):**
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

   The service will be available at `http://localhost:8000`

   **Note**: On Windows, you can use either PowerShell or CMD for these commands.

### Testing the API

You can test the endpoints using:

1. **FastAPI Interactive Docs**: Visit `http://localhost:8000/docs` for the automatic interactive API documentation

2. **Test Individual Tools**:
   - **Internal Tool**: `GET /tools/internal?destination=Goa` - Tests `get_destination_info`
   - **External Tool**: `GET /tools/external` - Tests `get_user_location`

3. **Test the Agent** (Task 3):
   - **POST /ask?query=what are the visiting place near me** - Should use both tools
   - **POST /ask?query=What's the region of my address?** - Should use `get_user_location`
   - **POST /ask?query=Which months are best to visit Bali?** - Should use `get_destination_info`

## Key Implementation Details

### Agent Setup

The project uses `create_react_agent` with `AgentExecutor` for robust agent execution:

- **LangChain Hub Integration**: Uses the official ReAct prompt (`hwchase17/react`) from LangChain Hub
- **Error Handling**: Includes `handle_parsing_errors=True` for graceful error recovery
- **Verbose Mode**: Enabled for detailed execution logs during development

### Tool Invocation Format

- **AgentExecutor**: Uses `{"input": "query"}` format and returns `{"output": "response"}`
- **Individual Tools**: Use `tool.invoke({"parameter": value})` format


