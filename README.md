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

1. Import required types from `typing` and `operator`
2. Create `DocumentationReflectionState` TypedDict with all required fields

**File:** `state.py`

## Task 2 — Implement LLM Initialization

### Goal

Set up Azure OpenAI LLM instance for generation, reflection, and refinement operations.

### Requirements

1. Import required modules
2. Load environment variables
3. Initialize AzureChatOpenAI with correct parameters
4. Export as `llm`

**File:** `llm.py`

## Task 3 — Implement Generation Node

### Goal

Build a generation node that creates initial technical documentation in README.md format.

### Requirements

1. Import required modules
2. Implement `generation_node` that generates documentation, cleans markdown, and updates state

**File:** `nodes/generation.py`

## Task 4 — Implement Reflection Node

### Goal

Build a reflection node that critically evaluates documentation on completeness, clarity, and examples.

### Requirements

1. Import required modules
2. Implement `reflection_node` that evaluates on three criteria, parses JSON response, and updates quality_score

**File:** `nodes/reflection.py`

## Task 5 — Implement Refinement Node

### Goal

Build a refinement node that improves documentation based on reflection critique.

### Requirements

1. Import required modules
2. Implement `refinement_node` that improves documentation based on feedback and increments iteration_count

**File:** `nodes/refinement.py`

## Task 6 — Implement Quality Gate Routing

### Goal

Build routing logic that determines whether to approve documentation or continue refining.

### Requirements

1. Import required modules
2. Implement `should_continue` that returns "approve" or "refine" based on quality and iterations

**File:** `routing.py`

## Task 7 — Build Reflection Graph

### Goal

Construct the complete LangGraph workflow with generation, reflection, and refinement nodes.

### Requirements

1. Import required modules
2. Implement `build_graph()` that creates StateGraph, adds nodes and edges, and returns compiled app

**File:** `graph.py`

## Task 8 — Implement FastAPI Endpoint

### Goal

Build REST API endpoint that processes documentation requests and returns structured results.

### Requirements

1. Import required modules
2. Configure logging
3. Create FastAPI app and build graph at startup
4. Define `DocumentationRequest` and `DocumentationResponse` BaseModels
5. Implement `POST /generate` endpoint


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
