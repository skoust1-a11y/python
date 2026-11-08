import logging
import re
from typing import Dict, Any, Optional, List
from main.services.mcp_client import HuggingFaceMCPService
from main.services.agent_factory import create_agent
from main.tools.custom_tools import custom_inference_tool
from llama_index.core.workflow import Context
from main.routes.routes import SentimentLabel

logger = logging.getLogger(__name__)


class AgentService:
    """Service to manage agent lifecycle and execute product review sentiment analysis"""
    
    def __init__(self):
        self.agent = None
        self.tools = []
        self._initialized = False
        self._mcp_connected = False
    
    async def initialize(self):
        """
        Initialize MCP connection and agent.
        
        TODO: Implement the following steps:
        1. Check if already initialized (return early if so)
        2. Initialize MCP Service
        3. Load MCP tools
        4. Add custom inference tool
        5. Create agent with tools
        6. Set initialization flags
        7. Handle exceptions appropriately
        """
        # TODO: Step 1 - Check if already initialized
        # Hint: Check if self._initialized is True
        # If true, log "Agent already initialized" and return early
        
        # TODO: Step 2 - Initialize MCP Service
        # Hint: Create an instance of HuggingFaceMCPService()
        # Store it in a variable named mcp_service
        
        # TODO: Step 3 - Load MCP tools
        # Hint: Call await mcp_service.load_tools(allowed_tools=None)
        # Store the result in self.tools
        # Log the number of tools loaded
        
        # TODO: Step 4 - Add custom inference tool
        # Hint: Append custom_inference_tool to self.tools list
        # Log that the hf_inference tool was added
        
        # TODO: Step 5 - Create agent
        # Hint: Call create_agent(self.tools, verbose=False)
        # Store the result in self.agent
        
        # TODO: Step 6 - Set initialization flags
        # Hint: Set self._initialized = True
        # Set self._mcp_connected = True
        # Log successful initialization
        
        # TODO: Step 7 - Handle exceptions
        # Hint: Wrap steps 2-6 in a try-except block
        # On exception, log the error with traceback and re-raise
        if self._initialized:
            logger.info("Agent already initialized")
            return

        try:
            mcp_service = HuggingFaceMCPService()

            self.tools = await mcp_service.load_tools(allowed_tools=None)
            logger.info(f"Loaded {len(self.tools)} MCP tools")

            self.tools.append(custom_inference_tool)
            logger.info("Added hf_inference custom tool")

            self.agent = create_agent(self.tools, verbose=False)

            self._initialized = True
            self._mcp_connected = True
            logger.info("Agent service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent service: {e}", exc_info=True)
            raise

    def is_initialized(self) -> bool:
        """Check if agent is initialized"""
        return self._initialized and self.agent is not None
    
    def is_mcp_connected(self) -> bool:
        """Check if MCP server is connected"""
        return self._mcp_connected
    
    def get_tools_count(self) -> int:
        """Get number of loaded tools"""
        return len(self.tools)
    
    async def analyze_review_sentiment(
        self, 
        review_text: str, 
        product_id: Optional[str] = None,
        product_name: Optional[str] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of a product review using MCP workflow.
        
        Args:
            review_text: Product review text to analyze
            product_id: Optional product identifier
            product_name: Optional product name for context
            verbose: Show detailed agent reasoning
            
        Returns:
            Dict with sentiment, confidence, model_used, aspects, and success status
        
        TODO: Implement the following steps:
        1. Check if agent is initialized (raise RuntimeError if not)
        2. Build product context string from product_name and product_id
        3. Create a prompt for the agent with instructions
        4. Create a Context and run the agent with the prompt
        5. Parse the agent response using _parse_response helper method
        6. Handle success and error cases appropriately
        """
        # TODO: Step 1 - Check if agent is initialized
        # Hint: Use self.is_initialized() method
        # If not initialized, raise RuntimeError with message "Agent service not initialized"
        
        # TODO: Step 2 - Build product context
        # Hint: Create an empty string for product_context
        # If product_name is provided, append " for product: {product_name}" to product_context
        # If product_id is provided, append " (ID: {product_id})" to product_context
        
        # TODO: Step 3 - Create prompt
        # Hint: Create a multi-line prompt string (f-string) that includes:
        # - The review text with product context
        # - Instructions for the agent to use 'model_search' MCP tool
        # - Instructions to use 'hf_inference' tool
        # - Instructions to extract aspects
        # - Format requirements for the response (Sentiment, Confidence, Model, Aspects)
        
        # TODO: Step 4 - Run the agent
        # Hint: Create a Context object with self.agent
        # Use self.agent.run(prompt, ctx=ctx) to get a handler
        # Await the handler to get the response
        # Convert the response to string and store in response_text
        
        # TODO: Step 5 - Parse the response
        # Hint: Call self._parse_response() with response_text, review_text, product_id, product_name
        # Store the result in a variable
        
        # TODO: Step 6 - Handle results
        # Hint: If result is truthy, set result["success"] = True and return it
        # If result is None/falsy, return a dictionary with:
        #   - sentiment: SentimentLabel.NEUTRAL
        #   - confidence: 0.0
        #   - model_used: "parsing_failed"
        #   - aspects: []
        #   - success: False
        #   - error: "Failed to parse agent response"
        #   - raw_response: response_text
        # Wrap in try-except to catch exceptions and return error dictionary
        if not self.is_initialized():
            raise RuntimeError("Agent service not initialized")

        try:
            product_context = ""
            if product_name:
                product_context += f" for product: {product_name}"
            if product_id:
                product_context += f" (ID: {product_id})"

            prompt = f"""Analyze the sentiment of the following product review{product_context}:

Review: "{review_text}"

Follow these steps:
1. Use the 'model_search' MCP tool to find a suitable Hugging Face sentiment analysis model for product reviews. Do NOT hardcode a model.
2. Use the 'hf_inference' tool with the discovered model ID and the review text to run sentiment classification.
3. Determine the overall sentiment as one of: POSITIVE, NEGATIVE, NEUTRAL, or MIXED.
4. Extract the key aspects mentioned in the review (e.g., price, quality, delivery, customer service). If none, say none.

Respond in EXACTLY this format:
Sentiment: <POSITIVE|NEGATIVE|NEUTRAL|MIXED>
Confidence: <a number between 0 and 1>
Model: <the model ID you used>
Aspects: <comma-separated list of aspects, or none>"""

            ctx = Context(self.agent)
            handler = self.agent.run(prompt, ctx=ctx)
            response = await handler
            response_text = str(response)

            result = self._parse_response(response_text, review_text, product_id, product_name)

            if result:
                result["success"] = True
                return result

            return {
                "sentiment": SentimentLabel.NEUTRAL,
                "confidence": 0.0,
                "model_used": "parsing_failed",
                "aspects": [],
                "success": False,
                "error": "Failed to parse agent response",
                "raw_response": response_text
            }
        except Exception as e:
            logger.error(f"Error during sentiment analysis: {e}", exc_info=True)
            return {
                "sentiment": SentimentLabel.NEUTRAL,
                "confidence": 0.0,
                "model_used": "error",
                "aspects": [],
                "success": False,
                "error": str(e)
            }
    
    
    
    def _parse_response(self, response: str, review_text: str, product_id: Optional[str], product_name: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Parse agent response to extract sentiment, confidence, model, and aspects.
        
        Note: The underscore prefix (_) indicates this is a private/internal method.
        It's not part of the public API and should only be called from within this class.
        
        TODO: Implement the following steps:
        1. Use regex to extract sentiment, confidence, model, and aspects from the response
        2. Map sentiment string to SentimentLabel enum
        3. Parse confidence score and model name
        4. Parse aspects list from comma-separated string
        5. Return a dictionary with all extracted information
        """
        # TODO: Step 1 - Extract information using regex
        # Hint: Use re.search() to find patterns in the response string
        # Search for "Sentiment: [value]" pattern (case-insensitive)
        # Search for "Confidence: [value]" pattern (case-insensitive)
        # Search for "Model: [value]" pattern (case-insensitive)
        # Search for "Aspects: [value]" pattern (case-insensitive)
        # Store matches in variables (sentiment_match, confidence_match, model_match, aspects_match)
        
        # TODO: Step 2 - Map sentiment to enum
        # Hint: If sentiment_match found, extract the matched group and convert to uppercase
        # Try to create SentimentLabel enum from the string
        # If ValueError, map common variations:
        #   - "POS" or "GOOD" -> SentimentLabel.POSITIVE
        #   - "NEG" or "BAD" -> SentimentLabel.NEGATIVE
        #   - "MIX" -> SentimentLabel.MIXED
        #   - Otherwise -> SentimentLabel.NEUTRAL
        
        # TODO: Step 3 - Parse confidence and model
        # Hint: Extract confidence from confidence_match.group(1) and convert to float
        # Use 0.0 as default if confidence_match is None
        # Extract model from model_match.group(1) or use "unknown" as default
        
        # TODO: Step 4 - Parse aspects
        # Hint: If aspects_match found, extract the matched group and strip whitespace
        # Check if the string is not "none" (case-insensitive) and not empty
        # Split by comma, strip each aspect, and filter out empty strings
        # Store in a list
        
        # TODO: Step 5 - Return dictionary
        # Hint: If sentiment_match was found, return a dictionary with:
        #   - sentiment: SentimentLabel enum value
        #   - confidence: float value
        #   - model_used: string value
        #   - aspects: list of strings
        #   - review_text: review_text parameter
        #   - product_id: product_id parameter
        #   - product_name: product_name parameter
        # If sentiment_match not found, return None
        # Wrap in try-except to handle errors and return None on exception
        try:
            sentiment_match = re.search(r"Sentiment:\s*(.+)", response, re.IGNORECASE)
            confidence_match = re.search(r"Confidence:\s*([0-9]*\.?[0-9]+)", response, re.IGNORECASE)
            model_match = re.search(r"Model:\s*(.+)", response, re.IGNORECASE)
            aspects_match = re.search(r"Aspects:\s*(.+)", response, re.IGNORECASE)

            if not sentiment_match:
                return None

            sentiment_str = sentiment_match.group(1).strip().upper()
            try:
                sentiment = SentimentLabel(sentiment_str)
            except ValueError:
                if "POS" in sentiment_str or "GOOD" in sentiment_str:
                    sentiment = SentimentLabel.POSITIVE
                elif "NEG" in sentiment_str or "BAD" in sentiment_str:
                    sentiment = SentimentLabel.NEGATIVE
                elif "MIX" in sentiment_str:
                    sentiment = SentimentLabel.MIXED
                else:
                    sentiment = SentimentLabel.NEUTRAL

            confidence = float(confidence_match.group(1)) if confidence_match else 0.0

            model_used = model_match.group(1).strip() if model_match else "unknown"

            aspects = []
            if aspects_match:
                aspects_str = aspects_match.group(1).strip()
                if aspects_str and aspects_str.lower() != "none":
                    aspects = [a.strip() for a in aspects_str.split(",") if a.strip()]

            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "model_used": model_used,
                "aspects": aspects,
                "review_text": review_text,
                "product_id": product_id,
                "product_name": product_name
            }
        except Exception as e:
            logger.error(f"Failed to parse agent response: {e}", exc_info=True)
            return None
