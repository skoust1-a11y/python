import os
from crewai import Agent, Task, Crew, Process, LLM
from models import ExpensePolicyResponse,ExpensePolicyRequest
from dotenv import load_dotenv

load_dotenv()


def _build_azure_llm() -> "LLM":
    """
    Build and return a configured Azure OpenAI LLM instance.

    TODOs:
    1. Read required Azure OpenAI configuration from environment variables.
    2. Validate that required values are present and raise ValueError if any are missing.
    3. Construct and return a CrewAI LLM configured for the Azure OpenAI provider.

    """
    # TODO: Step 1 - Read Azure OpenAI settings from environment
    # Hint: Use os.getenv for AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION.
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

    # TODO: Step 2 - Validate required configuration
    # Hint: Ensure API key, endpoint, and deployment name are not empty before proceeding.

    # TODO: Step 3 - Create and return the LLM instance
    # Hint: Use the LLM class from CrewAI with provider set to "azure_openai".
    llm = LLM(
        model=azure_deployment,
        provider="azure_openai",
        azure_endpoint=azure_endpoint,
        api_key=azure_api_key,
        api_version=azure_api_version,
        temperature=0.7,
    )
    return llm



def validate_expense_policy(request: ExpensePolicyRequest) -> str:
    """
    Create and execute the Expense Policy Validator hierarchical crew.

    Returns the final decision as a string.

    TODOs:
    1. Build the shared Azure OpenAI LLM using the helper function.
    2. Define specialist agents for Policy Interpreter and Expense Validator.
    3. Define the Finance Manager manager_agent.
    4. Build a single high-level Task that includes policy text and expense details from the request.
    5. Assemble a hierarchical Crew with the specialists and manager_agent.
    6. Execute the crew and return the final decision text.

    """
    # TODO: Step 1 - Build the Azure OpenAI LLM
    # Hint: Call the helper in this module to obtain the configured LLM instance.
    llm  = _build_azure_llm()

    # TODO: Step 2 - Create specialist agents
    # Hint: Define Policy Interpreter and Expense Validator agents using the shared LLM.
    policy_interpreter = Agent(
        role='Policy Interpreter',
        goal='Analyze company expense policies and determine if expenses comply with organizational guidelines. Provide clear, detailed interpretations of policy requirements.',
        backstory='You are an expert compliance officer with 10+ years of experience in corporate policy interpretation. You have deep knowledge of industry standards and best practices. Your role is to ensure that all expenses align with company guidelines and flag any policy violations.',
        llm=llm,
        verbose=True
    )
    expense_validator = Agent(
        role='Expense Validator',
        goal='Validate submitted expenses against approved budgets and policy guidelines. Verify receipts, amounts, and categorization. Recommend approval or rejection with clear reasoning.',
        backstory='You are a meticulous financial auditor with expertise in expense management and fraud detection. You have processed thousands of expense reports and can quickly identify anomalies. You ensure accuracy and fairness in the expense validation process.',
        llm=llm,
        verbose=True
    )

    # TODO: Step 3 - Create the Finance Manager manager_agent
    # Hint: Use an Agent with a manager role and goal; do not include it in the specialists list.
    finance_manager = Agent(
        role="Finance Director",
        goal="Oversee financial operations, ensure expense compliance, manage budgets, and provide financial insights for business decisions. Approve or reject expenses based on company policies and available funds.",
        backstory="You are a seasoned Finance Director with 15+ years of experience in corporate finance and budgeting. You have a keen eye for cost optimization and fraud prevention. Your decisions directly impact the company's bottom line, and you take that responsibility seriously.",
        llm=llm,
        verbose=True
    )


    # TODO: Step 4 - Build the high-level Task
    # Hint: Combine a short policy summary with fields from the ExpensePolicyRequest into the description.
    policy_summary = f"""
    Expense Request Details:
    - Amount: ${request.amount}
    - Category: {request.expense_type}
    - Receipt Provided: {request.receipt_provided}
    - Business Purpose: {request.business_purpose}
    - Policy Limit: ${request.policy_limit}
    """
    expected_output = """
    A detailed policy compliance report containing:
    1. Whether the expense complies with company policies
    2. Policy rules that apply to this expense category
    3. Any violations or concerns identified
    4. Final recommendation (APPROVED / REJECTED)
    5. Detailed reasoning for the decision
    """
    task = Task(
        description=policy_summary,
        expected_output=expected_output
    )

    # TODO: Step 5 - Assemble the hierarchical Crew
    # Hint: Use Process.hierarchical and pass manager_agent plus the specialists and single Task.
    crew = Crew(
        process=Process.hierarchical,
        agents=[policy_interpreter,expense_validator],
        tasks=[task],
        manager_agent=finance_manager,
        verbose=True
    )

    # TODO: Step 6 - Execute and return the decision
    # Hint: Run kickoff() on the Crew and return the string form of the result.
    return crew.kickoff()

