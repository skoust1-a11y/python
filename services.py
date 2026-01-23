import os
from dotenv import load_dotenv

from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool

load_dotenv()


def create_review_analysis_crew(product: str):
    """
    Create and execute a product review analysis crew for the given product.
    """
    
    # ------------------------------------------------------------------
    # Azure OpenAI configuration (STRICT)
    # ------------------------------------------------------------------
    # TODO: Load Azure OpenAI environment variables, validate them, and initialize LLM
    # Hint: Use os.getenv() to retrieve AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, 
    # AZURE_OPENAI_DEPLOYMENT_NAME, and AZURE_OPENAI_API_VERSION (default: "2024-02-15-preview")
    # Validate all required variables are present, raise ValueError if missing
    # Initialize LLM with model, provider="azure_openai", azure_endpoint, api_key, 
    # api_version, and temperature=0.3
    
    # ------------------------------------------------------------------
    # Initialize web search tool for review research
    # ------------------------------------------------------------------
    # TODO: Initialize SerperDevTool for web search
    # Hint: Use SerperDevTool() and store in search_tool variable
    
    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------
    # TODO: Create three agents:
    # 1. Review Researcher: role="Product Review Analyst", goal="Find and compile recent product reviews from multiple sources",
    #    appropriate backstory about finding authentic reviews, tools=[search_tool], llm, verbose=True, allow_delegation=False
    # 2. Sentiment Analyzer: role="Customer Sentiment Specialist", goal="Analyze review sentiment and extract key themes",
    #    appropriate backstory about reading between the lines, llm, verbose=True, allow_delegation=False
    # 3. Insights Reporter: role="Business Insights Writer", goal="Transform analysis into actionable business recommendations",
    #    appropriate backstory about translating data to insights, llm, verbose=True, allow_delegation=False
    
    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    # TODO: Create three tasks:
    # 1. Research Task: description to search for reviews of {product}, find 3-5 detailed reviews covering different aspects,
    #    expected_output describing compilation of 3-5 reviews with source references, agent=review_researcher, tools=[search_tool]
    # 2. Analyze Task: description to analyze sentiment, praised features, complaints, and recurring themes,
    #    expected_output describing structured analysis with sentiment scores and categorized themes, 
    #    agent=sentiment_analyzer, context=[research_task]
    # 3. Report Task: description to create executive summary with sentiment overview, key strengths, weaknesses, and recommendations,
    #    expected_output describing professional report (300-400 words) with actionable recommendations,
    #    agent=insights_reporter, context=[analyze_task], output_file="product_insights.md"
    
    # ------------------------------------------------------------------
    # Crew
    # ------------------------------------------------------------------
    # TODO: Create and return Crew
    # Hint: Use Crew() with agents list, tasks list, process=Process.sequential, verbose=True, tracing=True
    # Return crew.kickoff(inputs={"product": product})
    
    raise NotImplementedError("This function is not yet implemented. Please complete the TODO steps above.")
