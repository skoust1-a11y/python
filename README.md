## Project Context

You've already built the core travel suggestion engine in earlier practice — it can generate itineraries and structured outputs.  
Now, it's time to make your **Trip & Travel Agent** smarter by giving it **tools** it can use to fetch information, reason about data, and respond intelligently.


---

## Problem Statement

Equip your **Travel & Trip Planner Agent** with tools and intelligence by creating tools with internal logic and external API integration, then combining them into an intelligent agent that can automatically select and use the appropriate tools based on user queries.  
You will complete **three main tasks**:

---

### **Task 1 — Create and Test an Internal Tool (`get_destination_info`)**

#### Goal  
Create an internal tool that uses the Gemini LLM to fetch and summarize travel-related details for any destination.

#### Requirements  
1. Implement a tool function in `travel_tools.py` that uses an LLM to generate travel summaries for destinations, including information about visiting months, attractions, and notable features.

2. Make sure the function can be registered as a tool, returns structured data, and includes proper error handling.

3. Create a FastAPI POST endpoint `/tools/internal` that accepts destination input, invokes the tool, and returns the travel information as a JSON response.

---

### **Task 2 — Create and Test an External API Tool (`get_user_location`)**

#### Goal  
Create a LangChain tool that fetches the user's current location using an external geolocation API to provide localized recommendations.

#### Requirements  
1. Configure environment variables with the required API key for the external geolocation service.

2. Implement a tool function in `travel_tools.py` that connects to an external geolocation API and retrieves user location data (e.g., IP, city, region, country).

3. Ensure the function can be registered as a tool and includes proper error handling for API failures, network issues, and missing credentials.

4. Create a FastAPI endpoint `/tools/external` that invokes the tool and returns location data as a JSON response.

---

### **Task 3 — Build an Intelligent Travel Agent**

#### Goal  
Combine both tools into a single agent that automatically decides which tool(s) to use based on the user query.

#### Requirements  
1. Set up an agent using `create_agent` that combines both tools and is configured with a custom system prompt to guide tool selection based on user queries.

2. Configure the agent to automatically select the appropriate tool(s) for different query types (e.g., location-based queries, destination-specific queries).

3. Create a FastAPI POST endpoint `/ask` that accepts user queries, invokes the agent, and returns the agent's response.

---

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. Internal tool is correctly implemented with proper error handling and returns structured travel information.
2. External tool successfully connects to the external API and returns location data with proper error handling.
3. Both tools are properly decorated with `@tool` and can be invoked independently through their respective endpoints.
4. Agent is correctly configured with both tools and a custom system prompt.
5. Agent automatically selects the appropriate tool(s) based on different types of user queries.
6. All three endpoints (`/tools/internal`, `/tools/external`, `/ask`) correctly invoke their respective tools/agent and return appropriate responses.
