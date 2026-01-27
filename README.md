# Product Review Analysis

## Project Context

You're building a Product Review Analysis Crew, an AI-powered system that uses a 3-agent CrewAI crew to analyze product reviews, extract insights, and generate actionable business reports. The system uses role-based autonomous collaboration where specialized agents work together sequentially to research reviews, analyze sentiment, and produce executive summaries.

This practice focuses on building multi-agent crews with CrewAI — implementing agents with distinct roles, goals, and backstories, creating sequential tasks with context dependencies, integrating web search tools for review research, and exposing the crew as a REST API. You'll learn how to configure Azure OpenAI LLM for CrewAI, define specialized agents with tools, create tasks with automatic context passing, build crews with sequential processes, and implement FastAPI endpoints that process product review analysis requests.

## Problem Statement

Build a Product Review Analysis crew that responds to product names by searching for reviews, analyzing sentiment and themes, and generating actionable insights reports. You need to implement Azure OpenAI LLM configuration, web search tool integration, three specialized agents (Review Researcher, Sentiment Analyzer, Insights Reporter), three sequential tasks with context dependencies, crew assembly with sequential process, Pydantic request/response models, and FastAPI endpoints that process analysis requests and return structured results.

You will complete multiple implementation tasks to build this Product Review Analysis crew:

## Task 1 — Implement Crew Service

### Goal

Build the complete CrewAI crew service with LLM initialization, web search tool, three agents, three tasks, and crew assembly.

### Requirements

1. Load environment variables using `load_dotenv()`
2. Retrieve Azure OpenAI credentials from environment (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION)
3. Validate all required environment variables are present, raise ValueError if missing
4. Initialize LLM with Azure OpenAI configuration (model, provider="azure_openai", azure_endpoint, api_key, api_version, temperature=0.3)
5. Initialize SerperDevTool for web search
6. Create Review Researcher Agent with role="Product Review Analyst", goal="Find and compile recent product reviews from multiple sources", appropriate backstory, tools=[search_tool], llm, verbose=True, allow_delegation=False
7. Create Sentiment Analyzer Agent with role="Customer Sentiment Specialist", goal="Analyze review sentiment and extract key themes", appropriate backstory, llm, verbose=True, allow_delegation=False
8. Create Insights Reporter Agent with role="Business Insights Writer", goal="Transform analysis into actionable business recommendations", appropriate backstory, llm, verbose=True, allow_delegation=False
9. Create Research Task with description to search for reviews of {product}, find 3-5 detailed reviews covering different aspects, expected_output describing compilation of 3-5 reviews with source references, agent=review_researcher, tools=[search_tool]
10. Create Analyze Task with description to analyze sentiment, praised features, complaints, and recurring themes, expected_output describing structured analysis with sentiment scores and categorized themes, agent=sentiment_analyzer, context=[research_task]
11. Create Report Task with description to create executive summary with sentiment overview, key strengths, weaknesses, and recommendations, expected_output describing professional report (300-400 words) with actionable recommendations, agent=insights_reporter, context=[analyze_task], output_file="product_insights.md"
12. Create Crew with list of all three agents, list of all three tasks, process=Process.sequential, verbose=True, tracing=True
13. Return crew.kickoff(inputs={"product": product})

**File:** `services.py`

## Task 2 — Implement Pydantic Models

### Goal

Define request and response models for the FastAPI endpoint.

### Requirements

1. Import BaseModel and Field from pydantic
2. Create ProductReviewRequest with product field (str, required)
3. Create ProductReviewResponse with insights (str, required), status (str, default="success"), message (str, default="Review analysis completed successfully")

**File:** `models.py`

## Task 3 — Implement FastAPI Endpoint

### Goal

Build REST API endpoint that processes product review analysis requests.

### Requirements

1. Import ProductReviewRequest and ProductReviewResponse from models
2. Import create_review_analysis_crew from services
3. Validate product name is not empty in POST /analyze endpoint
4. Call create_review_analysis_crew with product name
5. Return ProductReviewResponse with insights from result.raw

**File:** `main.py`

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **Crew Service Implementation**: services.py loads environment variables with load_dotenv(), retrieves all required Azure OpenAI credentials from environment (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION), validates all required variables are present with ValueError if missing, creates LLM instance with model, provider="azure_openai", azure_endpoint, api_key, api_version, temperature=0.3, initializes SerperDevTool correctly, creates Review Researcher Agent with role="Product Review Analyst", goal="Find and compile recent product reviews from multiple sources", appropriate backstory, tools=[search_tool], llm, verbose=True, allow_delegation=False, creates Sentiment Analyzer Agent with role="Customer Sentiment Specialist", goal="Analyze review sentiment and extract key themes", appropriate backstory, llm, verbose=True, allow_delegation=False, creates Insights Reporter Agent with role="Business Insights Writer", goal="Transform analysis into actionable business recommendations", appropriate backstory, llm, verbose=True, allow_delegation=False, creates Research Task with description asking to search for reviews of {product} covering different aspects, expected_output describing compilation of 3-5 reviews with source references, agent=review_researcher, tools=[search_tool], creates Analyze Task with description to analyze sentiment, praised features, complaints, and recurring themes, expected_output describing structured analysis with sentiment scores and categorized themes, agent=sentiment_analyzer, context=[research_task], creates Report Task with description to create executive summary with sentiment overview, key strengths, weaknesses, and recommendations, expected_output describing professional report (300-400 words) with actionable recommendations, agent=insights_reporter, context=[analyze_task], output_file="product_insights.md", creates Crew with list of all three agents, list of all three tasks, process=Process.sequential, verbose=True, tracing=True, and returns crew.kickoff(inputs={"product": product}).

2. **Pydantic Models Implementation**: ProductReviewRequest BaseModel is defined with product field (str, required, description). ProductReviewResponse BaseModel is defined with insights (str, required), status (str, default="success"), message (str, default="Review analysis completed successfully").

3. **FastAPI Endpoint Implementation**: POST /analyze endpoint validates product name is not empty, calls create_review_analysis_crew with product name, handles exceptions with HTTPException, returns ProductReviewResponse with insights from result.raw, status="success", and appropriate message.
