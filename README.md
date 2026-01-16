## Project Context

You're building a Technical Documentation Generator, an AI-powered system that generates comprehensive documentation for Python code and iteratively improves it through self-reflection until quality standards are met. The system uses a Reflection pattern to generate initial documentation, critically evaluate it for completeness and clarity, and refine it until quality criteria are satisfied.

This practice focuses on building Self-Correcting agents with LangGraph — implementing generation nodes that create initial documentation, reflection nodes that critique documentation quality, refinement nodes that improve documentation based on feedback, and conditional routing based on quality scores. You'll learn how to create state schemas with reflection tracking fields, build generation prompts that create structured documentation, implement reflection logic that evaluates on multiple criteria, design refinement mechanisms that address specific issues, and implement quality gates that determine when to approve or continue refining.

## Problem Statement

Build a Reflection-based technical documentation generator that responds to code snippets by creating initial documentation, evaluating it on completeness, clarity, and examples, refining it based on critique, and approving when quality threshold is met. You need to implement state schemas with draft output and reflection feedback tracking, generation prompts that create README.md format documentation, graph nodes for generation, reflection, and refinement, conditional routing based on quality scores, and FastAPI endpoints that process documentation requests and return structured results.

You will complete multiple implementation tasks to build this Self-Correcting documentation agent:

## Task 1 — Implement State Schema

### Goal

Define the state schema that tracks documentation generation, reflection feedback, iterations, and quality scores.

### Requirements

1. Import `TypedDict`, `Annotated`, `List` from `typing` and `operator`
2. Create `DocumentationReflectionState` class extending `TypedDict` with fields: `messages` (Annotated[list, operator.add]), `task_description` (str), `draft_output` (str), `reflection_feedback` (Annotated[List[str], operator.add]), `iteration_count` (int), `quality_score` (float), `quality_threshold` (float), `max_iterations` (int), `output_approved` (bool)

**File:** `state.py`

## Task 2 — Implement LLM Initialization

### Goal

Set up Azure OpenAI LLM instance for generation, reflection, and refinement operations.

### Requirements

1. Import `AzureChatOpenAI` from `langchain_openai`, `load_dotenv` from `dotenv`, and `os`
2. Call `load_dotenv()` to load environment variables
3. Get Azure OpenAI credentials from environment: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_MODEL`, `AZURE_OPENAI_API_VERSION`
4. Create `AzureChatOpenAI` instance with api_key, azure_endpoint, model, api_version, temperature=0, max_retries=3, timeout=60
5. Export as `llm` variable

**File:** `llm.py`

## Task 3 — Implement Generation Node

### Goal

Build a generation node that creates initial technical documentation in README.md format.

### Requirements

1. Import `HumanMessage`, `SystemMessage` from `langchain_core.messages`, `DocumentationReflectionState` from `state`, and `llm` from `llm`
2. Implement `generation_node(state: DocumentationReflectionState)` that extracts `task_description` from state, builds generation prompt requesting README.md format with project overview, installation instructions, usage examples, and API documentation, uses beginner-friendly language and markdown format, invokes `llm.invoke()` with SystemMessage (expert technical writer) and HumanMessage (prompt), extracts documentation from response.content, cleans markdown code fences (handles ```markdown and ```), stores documentation in `state["draft_output"]`, initializes `state["iteration_count"]` to 0, sets `state["output_approved"]` to False, and returns updated state

**File:** `nodes/generation.py`

## Task 4 — Implement Reflection Node

### Goal

Build a reflection node that critically evaluates documentation on completeness, clarity, and examples.

### Requirements

1. Import `json`, `SystemMessage`, `HumanMessage` from `langchain_core.messages`, `DocumentationReflectionState` from `state`, and `llm` from `llm`
2. Implement `reflection_node(state: DocumentationReflectionState)` that extracts `task_description` and `draft_output` from state, builds critique prompt evaluating on three criteria (0-10 each): Completeness (all sections present: overview, installation, usage, API), Clarity (easy to understand, well-structured), Examples (sufficient working code examples), requests JSON format with scores, issues, suggestions, and overall_score, invokes `llm.invoke()` with SystemMessage (critical reviewer) and HumanMessage (critique prompt), parses JSON from response.content (removes ```json and ``` fences, handles JSONDecodeError), extracts `overall_score` from critique, creates feedback string with iteration number and summary, appends feedback to `state["reflection_feedback"]`, updates `state["quality_score"]` with overall_score, handles JSONDecodeError with fallback score 5.0, and returns updated state

**File:** `nodes/reflection.py`

## Task 5 — Implement Refinement Node

### Goal

Build a refinement node that improves documentation based on reflection critique.

### Requirements

1. Import `SystemMessage`, `HumanMessage` from `langchain_core.messages`, `DocumentationReflectionState` from `state`, and `llm` from `llm`
2. Implement `refinement_node(state: DocumentationReflectionState)` that extracts `task_description`, `draft_output`, and latest feedback from `state["reflection_feedback"][-1]`, builds refinement prompt with original task, current documentation, and critique, instructs to address all identified issues while keeping what works well, invokes `llm.invoke()` with SystemMessage (improvement specialist) and HumanMessage (refinement prompt), extracts refined documentation from response.content, cleans markdown code fences (handles ```markdown and ```), updates `state["draft_output"]` with refined documentation, increments `state["iteration_count"]`, and returns updated state

**File:** `nodes/refinement.py`

## Task 6 — Implement Quality Gate Routing

### Goal

Build routing logic that determines whether to approve documentation or continue refining.

### Requirements

1. Import `DocumentationReflectionState` from `state`
2. Implement `should_continue(state: DocumentationReflectionState) -> str` that extracts `quality_score`, `iteration_count`, `max_iterations`, and `quality_threshold` from state, checks if `iteration_count >= max_iterations` (sets `state["output_approved"]` to True and returns "approve"), checks if `quality_score >= quality_threshold` (sets `state["output_approved"]` to True and returns "approve"), checks if `7.0 <= quality_score < quality_threshold` (sets `state["output_approved"]` to True and returns "approve" for borderline cases), otherwise returns "refine" to continue improving

**File:** `routing.py`

## Task 7 — Build Reflection Graph

### Goal

Construct the complete LangGraph workflow with generation, reflection, and refinement nodes.

### Requirements

1. Import `StateGraph`, `END` from `langgraph.graph`, `DocumentationReflectionState` from `state`, and all node functions from `nodes` package, and `should_continue` from `routing`
2. Implement `build_graph()` that creates `StateGraph` with `DocumentationReflectionState`, adds nodes: "generator" (generation_node), "reflector" (reflection_node), "refiner" (refinement_node), sets entry point to "generator", adds edge from "generator" to "reflector", adds conditional edges from "reflector" using `should_continue` function with mapping: "refine" -> "refiner", "approve" -> END, adds edge from "refiner" to "reflector" (loop back), compiles graph with `workflow.compile()`, and returns compiled app

**File:** `graph.py`

## Task 8 — Implement FastAPI Endpoint

### Goal

Build REST API endpoint that processes documentation requests and returns structured results.

### Requirements

1. Import `logging`, `time`, `asyncio`, `FastAPI`, `HTTPException` from `fastapi`, `BaseModel` from `pydantic`, `build_graph` from `graph`, and `uvicorn`
2. Configure logging with StreamHandler and FileHandler('agent.log')
3. Create FastAPI app with title, description, and version
4. Build graph at startup and store in `doc_graph` variable
5. Define `DocumentationRequest` BaseModel with `task_description` (str), `quality_threshold` (float, default 8.0), `max_iterations` (int, default 3)
6. Define `DocumentationResponse` BaseModel with `status` (str), `task_description` (str), `generated_documentation` (str), `reflection_history` (list[str]), `iterations` (int), `final_quality_score` (float), `approved` (bool), `execution_time` (float)
7. Implement `POST /generate` endpoint that accepts `DocumentationRequest`, validates task_description (raises HTTPException if empty), initializes state with all required fields, invokes graph with timeout using `asyncio.wait_for` and `asyncio.to_thread` (timeout 300 seconds, recursion_limit 50), handles `TimeoutError` and general `Exception`, creates `DocumentationResponse` with results, prints formatted output to console (task, status, metrics, documentation, reflection history), and returns response
8. Implement `GET /health` endpoint that returns `{"status": "healthy", "service": "Technical Documentation Generator with Self-Correction"}`

**File:** `main.py`

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **State Schema Implementation**: DocumentationReflectionState class extends TypedDict correctly, includes all required fields with correct types (messages with Annotated[list, operator.add], task_description as str, draft_output as str, reflection_feedback with Annotated[List[str], operator.add], iteration_count as int, quality_score as float, quality_threshold as float, max_iterations as int, output_approved as bool), and all fields are properly typed.

2. **LLM Initialization Implementation**: llm.py loads environment variables with load_dotenv(), retrieves all required Azure OpenAI credentials from environment, creates AzureChatOpenAI instance with correct parameters (api_key, azure_endpoint, model, api_version, temperature=0, max_retries=3, timeout=60), and exports llm variable correctly.

3. **Generation Node Implementation**: generation_node function has correct signature accepting DocumentationReflectionState parameter. Function extracts task_description from state, builds comprehensive generation prompt requesting README.md format with overview, installation, usage examples, and API docs, uses beginner-friendly language instruction, invokes llm.invoke() with SystemMessage and HumanMessage, extracts documentation from response.content, cleans markdown code fences (handles ```markdown and ``` cases), stores documentation in draft_output, initializes iteration_count to 0, sets output_approved to False, and returns updated state.

4. **Reflection Node Implementation**: reflection_node function has correct signature accepting DocumentationReflectionState parameter. Function extracts task_description and draft_output from state, builds critique prompt evaluating on three criteria (Completeness, Clarity, Examples) with 0-10 scoring, requests JSON format with scores, issues, suggestions, and overall_score, invokes llm.invoke() with SystemMessage and HumanMessage, parses JSON from response.content (removes markdown fences, handles JSONDecodeError), extracts overall_score from critique, creates feedback string with iteration number and summary, appends feedback to reflection_feedback, updates quality_score with overall_score, handles JSONDecodeError with fallback score 5.0, and returns updated state.

5. **Refinement Node Implementation**: refinement_node function has correct signature accepting DocumentationReflectionState parameter. Function extracts task_description, draft_output, and latest feedback from reflection_feedback[-1], builds refinement prompt with original task, current documentation, and critique, instructs to address issues while keeping what works, invokes llm.invoke() with SystemMessage and HumanMessage, extracts refined documentation from response.content, cleans markdown code fences, updates draft_output with refined documentation, increments iteration_count, and returns updated state.

6. **Routing Function Implementation**: should_continue function has correct signature accepting DocumentationReflectionState parameter and returns str. Function extracts quality_score, iteration_count, max_iterations, and quality_threshold from state, checks iteration_count >= max_iterations (sets output_approved to True, returns "approve"), checks quality_score >= quality_threshold (sets output_approved to True, returns "approve"), checks borderline case 7.0 <= quality_score < quality_threshold (sets output_approved to True, returns "approve"), otherwise returns "refine", and handles all edge cases correctly.

7. **Graph Construction Implementation**: build_graph function creates StateGraph with DocumentationReflectionState schema. All nodes are registered correctly (generator, reflector, refiner). Entry point is set to "generator". Edge is added from "generator" to "reflector". Conditional edges are added from "reflector" using should_continue function with proper mapping (refine->refiner, approve->END). Edge is added from "refiner" to "reflector" for loop back. Graph is compiled correctly and returned.

8. **FastAPI Endpoint Implementation**: FastAPI app is created with title, description, and version. Graph is built at startup and stored in doc_graph. DocumentationRequest BaseModel is defined with correct fields and defaults. DocumentationResponse BaseModel is defined with all required fields. POST /generate endpoint is decorated correctly, accepts DocumentationRequest, validates task_description, initializes state correctly with all required fields, invokes graph with timeout using asyncio.wait_for and asyncio.to_thread, handles TimeoutError, handles general Exception, creates DocumentationResponse with results, prints formatted output to console, and returns response. GET /health endpoint returns correct response. Server runs correctly with uvicorn.
