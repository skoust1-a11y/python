import logging
import os
from typing import List, Any
from llama_index.core.tools import BaseTool

try:
    from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
except ImportError:
    logging.warning("llama-index-tools-mcp not found. Ensure dependencies are installed.")
    BasicMCPClient = Any
    McpToolSpec = Any

logger = logging.getLogger(__name__)

class HuggingFaceMCPService:
    """
    Service to handle connections to the Hugging Face MCP Server.
    """

    def __init__(self) -> None:
        """
        Initialize the service with configuration credentials.
        
        TODO: Implement the following steps:
        1. Get the MCP server URL from environment variable with a default value
        2. Get the Hugging Face token from environment variable
        3. Validate that the token is set (raise ValueError if not)
        4. Set up authorization headers with the token
        """
        # TODO: Step 1 - Get MCP server URL
        # Hint: Use os.getenv() to get "HF_MCP_URL" with default value "https://huggingface.co/mcp"
        # Store it in self.url
        
        # TODO: Step 2 - Get Hugging Face token
        # Hint: Use os.getenv() to get "HF_TOKEN"
        # Store it in self.token
        
        # TODO: Step 3 - Validate token
        # Hint: Check if self.token is not set
        # If not set, raise ValueError with a helpful message about setting HF_TOKEN
        # Include a link to https://huggingface.co/settings/tokens in the error message
        
        # TODO: Step 4 - Set up authorization headers
        # Hint: Create a dictionary with "Authorization" key
        # Value should be "Bearer {token}" formatted string
        # Store it in self.headers
        
        raise NotImplementedError("This method is not yet implemented. Please complete the TODO steps above.")

    async def load_tools(self, allowed_tools: List[str] | None = None) -> List[BaseTool]:
        """
        Connects to the remote MCP server and wraps capabilities as LlamaIndex tools.

        Args:
            allowed_tools (List[str] | None): A list of tool names to filter (e.g., ['model_search']).
                                              If None, returns all discovered tools.

        Returns:
            List[BaseTool]: A list of executable LlamaIndex tools.

        Raises:
            ConnectionError: If connection to MCP server fails.
        
        TODO: Implement the following steps:
        1. Log the connection attempt with the MCP server URL
        2. Initialize the MCP client with URL and headers
        3. Create a tool spec wrapper from the client
        4. Get all tools asynchronously from the tool spec
        5. Filter tools if allowed_tools is provided
        6. Handle exceptions and raise ConnectionError on failure
        """
        # TODO: Step 1 - Log connection attempt
        # Hint: Use logger.info() to log a message about connecting to the MCP server
        # Include self.url in the log message
        
        # TODO: Step 2 - Initialize MCP client
        # Hint: Create a BasicMCPClient instance
        # Pass command_or_url=self.url and headers=self.headers as parameters
        # Store it in a variable named client
        
        # TODO: Step 3 - Create tool spec wrapper
        # Hint: Create a McpToolSpec instance with client=client
        # Store it in a variable named tool_spec
        
        # TODO: Step 4 - Get all tools asynchronously
        # Hint: Use await tool_spec.to_tool_list_async() to get all tools
        # Store the result in a variable named tools
        
        # TODO: Step 5 - Filter tools if needed
        # Hint: Check if allowed_tools is provided (not None)
        # If provided, filter tools where t.metadata.name is in allowed_tools
        # Return the filtered tools
        # If not provided, return all tools
        
        # TODO: Step 6 - Handle exceptions
        # Hint: Wrap the above steps in a try-except block
        # On exception, log the error and raise ConnectionError with an appropriate message
        
        raise NotImplementedError("This method is not yet implemented. Please complete the TODO steps above.")
