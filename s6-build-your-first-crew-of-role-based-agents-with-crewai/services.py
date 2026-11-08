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
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    azure_api_version = os.getenv(
        "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
    )

    if not all([azure_api_key, azure_endpoint, azure_deployment]):
        raise ValueError(
            "Missing Azure OpenAI configuration.\n"
            "Required env vars:\n"
            "- AZURE_OPENAI_API_KEY\n"
            "- AZURE_OPENAI_ENDPOINT\n"
            "- AZURE_OPENAI_DEPLOYMENT_NAME\n"
            "Optional:\n"
            "- AZURE_OPENAI_API_VERSION"
        )
    
    llm = LLM(
        model=azure_deployment, 
        provider="azure_openai",
        azure_endpoint=azure_endpoint,
        api_key=azure_api_key,
        api_version=azure_api_version,
        temperature=0.3,
    )


    
    # ------------------------------------------------------------------
    # Initialize web search tool for review research
    # ------------------------------------------------------------------
    # TODO: Initialize SerperDevTool for web search
    # Hint: Use SerperDevTool() and store in search_tool variable
    search_tool = SerperDevTool()
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
    review_researcher = Agent(
        role = 'Product Review Analyst',
        goal = 'Find and compile recent product reviews from multiple sources',
        backstory = 'You are good in finding authentic reviews',
        tools = [search_tool],
        llm = llm,
        verbose = True,
        allow_delegation = False
    )
    sentiment_analyzer = Agent(
        role  = "Customer Sentiment Specialist",
        goal = "Analyze review sentiment and extract key themes",
        backstory = 'You are excellent sentiment analyzer and you extract the sentiment easily and also read betwwen the lines easily',
        llm = llm,
        verbose = True,
        allow_delegation = False
        )
    insights_reporter = Agent(
        role = 'Business Insights Writer',
        goal = 'transform analysis into actionable business recommendations',
        backstory= 'You are a excellent in translating data to insights',
        llm = llm,
        verbose = True,
        allow_delegation = False
    )
    
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
    research_task = Task(
        agent=review_researcher,
        tools=[search_tool],
        description=f'search for reviews of {product},and find 3-5 detailed reviews covering different aspects',
        expected_output='compilation of 3-5 reviews with source references'
    )
    analyze_task = Task(
        agent=sentiment_analyzer,
        description='analyze sentiment, praised features, complaints, and recurring themes',
        expected_output='structured analysis with sentiment scores and categorized themes',
        context=[research_task]
    )
    report_task = Task(
        agent=insights_reporter,
        description='create executive summary with sentiment overview, key strengths, weaknesses, and recommendations',
        expected_output='professional report (300-400 words) with actionable recommendations',
        context=[analyze_task],
        output_file="product_insights.md"
    )
    
    # ------------------------------------------------------------------
    # Crew
    # ------------------------------------------------------------------
    # TODO: Create and return Crew
    # Hint: Use Crew() with agents list, tasks list, process=Process.sequential, verbose=True, tracing=True
    # Return crew.kickoff(inputs={"product": product})
    crew = Crew(
        agents=[review_researcher,sentiment_analyzer,insights_reporter],
        tasks=[research_task,analyze_task,report_task],
        process=Process.sequential,
        verbose=True,
        tracing=True,

    )
    return crew.kickoff(inputs={"product":product})
