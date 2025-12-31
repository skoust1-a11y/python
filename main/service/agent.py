"""
Agent Service - Creates and manages the OpenAI agent for healthcare analytics
"""
import os
from dotenv import load_dotenv
from llama_index.agent.openai import OpenAIAgent
from llama_index.core import Settings
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding

from main.service.tools import get_sql_tool, get_vector_tool


load_dotenv()


# Global agent instance (initialized once)
_agent = None


def get_agent():
    """
    Get or create the OpenAI agent with SQL and Vector tools.
    
    Returns:
        OpenAIAgent instance configured with SQL and Vector tools
    
    TODO: Implement the following steps:
    1. Check if the global agent instance is None
    2. Initialize the Azure OpenAI LLM and set it in Settings
    3. Initialize the Azure OpenAI embedding model and set it in Settings
    4. Get the SQL tool and Vector tool instances
    5. Create a list containing both tools
    6. Create the OpenAIAgent with tools, verbose mode, and system prompt
    7. Store the agent in the global variable and return it
    """
    global _agent

    # TODO: Step 1 - Check if the global agent instance is None
    # Hint: Check whether the global _agent variable is None. This function uses a singleton pattern, so it should only create
    # the agent once. If _agent is not None, it means the agent has already been created and you should skip the initialization
    # steps and return the existing agent. If _agent is None, proceed with the initialization steps below.
    
    # TODO: Step 2 - Initialize the Azure OpenAI LLM and set it in Settings
    # Hint: Create an AzureOpenAI instance by instantiating the AzureOpenAI class. You need to provide several parameters by
    # retrieving them from environment variables using os.getenv. The model parameter should use "AZURE_OPENAI_LLM_DEPLOYMENT",
    # the deployment_name should also use "AZURE_OPENAI_LLM_DEPLOYMENT", the api_key should use "AZURE_OPENAI_API_KEY",
    # the azure_endpoint should use "AZURE_OPENAI_ENDPOINT", and the api_version should use "AZURE_OPENAI_API_VERSION".
    # Store the created LLM instance in a variable, then assign it to Settings.llm so it can be used throughout the application.
    
    # TODO: Step 3 - Initialize the Azure OpenAI embedding model and set it in Settings
    # Hint: Create an AzureOpenAIEmbedding instance by instantiating the AzureOpenAIEmbedding class. Similar to the LLM, you need
    # to provide parameters from environment variables. The model parameter should use "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", the
    # deployment_name should also use "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", the api_key should use "AZURE_OPENAI_API_KEY",
    # the azure_endpoint should use "AZURE_OPENAI_ENDPOINT", and the api_version should use "AZURE_OPENAI_API_VERSION".
    # Store the created embedding model instance in a variable, then assign it to Settings.embed_model.
    
    # TODO: Step 4 - Get the SQL tool and Vector tool instances
    # Hint: Call the get_sql_tool function that has been imported at the top of this file to retrieve the SQL database tool.
    # Store the result in a variable. Call the get_vector_tool function that has also been imported to retrieve the vector
    # document search tool. Store this result in another variable. Both of these functions return QueryEngineTool instances that
    # will be used by the agent.
    
    # TODO: Step 5 - Create a list containing both tools
    # Hint: Create a list that contains both the SQL tool and the vector tool you retrieved in the previous step. This list will
    # be passed to the agent constructor so the agent knows which tools are available for use.
    
    # TODO: Step 6 - Create the OpenAIAgent with tools, verbose mode, and system prompt
    # Hint: Use the OpenAIAgent.from_tools class method to create an agent instance. Pass the tools list you created in the previous
    # step as the first argument. Set the verbose parameter to True so the agent will provide detailed output during execution.
    # Provide a system_prompt parameter with a multi-line string that defines the agent's role and behavior. The system prompt should
    # explain that the agent is a healthcare analytics assistant, provide tool usage guidelines explaining when to use each tool,
    # and include important instructions about comparing metrics, citing sources, protecting patient privacy, and providing actionable
    # insights. Store the created agent instance in the global _agent variable.
    
    # TODO: Step 7 - Store the agent in the global variable and return it
    # Hint: Return the _agent variable. Since you stored the agent in _agent in the previous step, you can simply return it.
    # If the agent was already created (Step 1 check passed), return the existing _agent without going through the initialization steps.
    
    raise NotImplementedError("This function is not yet implemented. Please complete the TODO steps above.")
