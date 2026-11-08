# Product Review Sentiment Analysis with MCP Integration

## Project Context

You're building a **Product Review Sentiment Analysis API**, an AI-powered system that analyzes customer product reviews to determine sentiment (POSITIVE, NEGATIVE, NEUTRAL, MIXED), extract key aspects (price, quality, delivery, etc.), and provide confidence scores. The system uses **Model Context Protocol (MCP)** to dynamically discover and use Hugging Face sentiment analysis models at runtime, without hardcoding any specific models.

This practice focuses on **MCP integration** — connecting to remote MCP servers, loading tools dynamically, creating autonomous agents that can discover and use ML models, and building a production-ready REST API with comprehensive error handling.

## Problem Statement

Build a production-ready sentiment analysis API that can analyze product reviews using dynamically discovered ML models via MCP. The key challenges are:

1. **MCP Integration**: Connecting to remote Hugging Face MCP servers and loading tools programmatically
2. **Dynamic Model Discovery**: Using MCP tools to discover sentiment analysis models at runtime without hardcoding
3. **Agent Orchestration**: Creating autonomous agents that can reason, search for models, and execute inference
4. **Response Parsing**: Extracting structured information (sentiment, confidence, aspects) from agent responses
5. **Error Handling**: Gracefully handling connection failures, model errors, and parsing issues

You will complete the following implementation tasks to build the sentiment analysis system with MCP integration:

---

### **Task 1 — Initialize MCP Service**

#### Goal

Set up the HuggingFaceMCPService by loading configuration credentials and setting up authentication headers.

#### Requirements

1. Load MCP server URL from environment variable with default fallback
2. Load Hugging Face authentication token from environment variable
3. Validate token presence and raise ValueError with descriptive error message if missing
4. Construct authorization headers dictionary with Bearer token authentication

**File**: `main/services/mcp_client.py` → `__init__()`

---

### **Task 2 — Load MCP Tools**

#### Goal

Connect to the remote MCP server and load available tools as LlamaIndex FunctionTools.

#### Requirements

1. Instantiate BasicMCPClient with server URL and authentication headers
2. Create McpToolSpec wrapper from MCP client instance
3. Retrieve all available tools asynchronously from the tool specification
4. Apply optional tool filtering based on allowed_tools parameter
5. Return filtered or complete tool list as BaseTool instances

**File**: `main/services/mcp_client.py` → `load_tools()`

---

### **Task 3 — Create ReAct Agent**

#### Goal

Create a ReActAgent instance configured with tools and LLM for autonomous model discovery and inference.

#### Requirements

1. Initialize LLM instance via create_llm() factory function
2. Instantiate ReActAgent with provided tools and configured LLM
3. Return configured ReActAgent instance ready for execution

**File**: `main/services/agent_factory.py` → `create_agent()`

---

### **Task 4 — Implement HF Inference API Function**

#### Goal

Create the main inference function that routes to appropriate implementation based on library availability.

#### Requirements

1. Determine library availability via HF_HUB_AVAILABLE flag
2. Route to hub client implementation if available, otherwise use requests fallback
3. Return JSON-formatted inference result or error message

**File**: `main/tools/custom_tools.py` → `hf_inference_api()`

---

### **Task 5 — Implement Hub Client Inference**

#### Goal

Implement inference using the HuggingFace Hub client library for text classification.

#### Requirements

1. Load and validate Hugging Face authentication token from environment
2. Return structured JSON error response if token is missing
3. Initialize InferenceClient with authentication token
4. Execute text classification inference
5. Transform classification results into JSON format with label and score fields
6. Return structured error response with model information and recovery suggestions on failure

**File**: `main/tools/custom_tools.py` → `_call_with_hub_client()`

---

### **Task 6 — Implement Requests-Based Inference**

#### Goal

Implement fallback inference method using requests library directly for HuggingFace Inference API.

#### Requirements

1. Load and validate Hugging Face token from environment
2. Construct HuggingFace Inference API endpoint URL
3. Configure HTTP request headers with Bearer authentication and content type
4. Prepare request payload with input text
5. Execute POST request with timeout configuration
6. Handle response status codes with retry logic for loading models
7. Return structured error responses on failure

**File**: `main/tools/custom_tools.py` → `_call_with_requests()`

---

### **Task 7 — Create LlamaIndex Tool**

#### Goal

Create a FunctionTool from the hf_inference_api function for use by the agent.

#### Requirements

1. Create FunctionTool instance using FunctionTool.from_defaults() factory method
2. Configure tool with hf_inference_api function reference
3. Set tool identifier as "hf_inference"
4. Define comprehensive tool description including usage constraints, optimization details, error handling instructions, parameter specifications, and return value format
5. Assign tool instance to custom_inference_tool module variable

**File**: `main/tools/custom_tools.py` → `custom_inference_tool`

---

### **Task 8 — Initialize Agent Service**

#### Goal

Set up the agent service by connecting to MCP, loading tools, and creating the agent.

#### Requirements

1. Implement idempotent initialization check with early return
2. Instantiate HuggingFaceMCPService for MCP connectivity
3. Load MCP tools asynchronously and store in instance variable
4. Integrate custom inference tool into tool collection
5. Create ReActAgent instance with configured tools
6. Set service state flags for initialization and MCP connectivity

**File**: `main/services/agent_service.py` → `initialize()`

---

### **Task 9 — Implement Review Sentiment Analysis**

#### Goal

Orchestrate the complete sentiment analysis pipeline: prompt creation → agent execution → response parsing.

#### Requirements

1. Validate agent initialization state prior to processing
2. Build product context string from optional product_name and product_id parameters
3. Construct multi-line prompt with review text, model search instructions, inference tool usage, aspect extraction requirements, and response format specifications
4. Create Context object and execute agent with prompt
5. Parse agent response using \_parse_response helper method
6. Return structured result dictionary with success flag or error response

**File**: `main/services/agent_service.py` → `analyze_review_sentiment()`

---

### **Task 10 — Parse Agent Response**

#### Goal

Extract structured information (sentiment, confidence, model, aspects) from the agent's text response using regex.

#### Requirements

1. Extract sentiment, confidence, model, and aspects patterns from response string using regex
2. Map extracted sentiment string to SentimentLabel enum with variation handling
3. Parse confidence score as float with default value
4. Extract model identifier with default fallback
5. Parse aspects list from comma-separated string with validation
6. Return structured dictionary with all extracted fields or None if parsing fails

**File**: `main/services/agent_service.py` → `_parse_response()`

---

### **Task 11 — Implement Review Analysis API Endpoint**

#### Goal

Create a FastAPI endpoint that accepts product review requests and returns structured sentiment analysis responses.

#### Requirements

1. Validate agent service initialization state prior to processing requests
2. Invoke agent_service.analyze_review_sentiment() with request parameters
3. Validate result success status and handle failure cases appropriately
4. Transform service response dictionary into SentimentResponse Pydantic model
5. Implement exception handling for proper error propagation

**File**: `main/routes/routes.py` → `analyze_review()`

---

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **MCP Service Initialization**: The HuggingFaceMCPService successfully initializes with URL and token from environment variables, validates token presence, and sets up authorization headers correctly.

2. **MCP Tools Loading**: The load_tools method successfully connects to the MCP server, creates BasicMCPClient and McpToolSpec instances, retrieves tools asynchronously, and handles filtering when allowed_tools is provided.

3. **Agent Creation**: The create_agent function successfully creates a ReActAgent instance with the provided tools and LLM from create_llm().

4. **Inference Functions**: The hf_inference_api function correctly routes to hub client or requests-based implementation, both implementations handle token validation, API calls, and error responses appropriately.

5. **Tool Creation**: The custom_inference_tool is successfully created using FunctionTool.from_defaults() with proper function, name, and description.

6. **Agent Service Initialization**: The initialize method successfully connects to MCP, loads tools, adds custom inference tool, creates agent, and sets initialization flags with proper error handling.

7. **Sentiment Analysis Pipeline**: The analyze_review_sentiment method correctly validates initialization, builds prompts, executes agent, parses responses, and returns structured results with success/error handling.

8. **End-to-End Flow**: The complete system processes review queries through initialization → MCP connection → tool loading → agent creation → query execution → response parsing → API response, returning structured sentiment analysis with all required fields.
