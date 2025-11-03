"""
Orchestrator Agent - Central Coordination Hub

Coordinates all AI services:
- Prompt Manager (gRPC)
- Ollama Service (gRPC)
- Gemini API (HTTP)
"""

import logging
from typing import Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Coordinates all AI services and manages workflow."""
    
    def __init__(
        self,
        prompt_manager_address: str = "localhost:50051",
        ollama_service_address: str = "localhost:50052",
        gemini_client: Optional[OpenAI] = None,
        gemini_model: str = "gemini-2.0-flash",
        ollama_model: str = "gemma3:270m"
    ):
        """Initialize connections to all services."""
        logger.info("Initializing Orchestrator Agent")
        
        # Write code to Connect to services
        
        # Once connected, log success messages
        logger.info(f"Connected to Prompt Manager: {prompt_manager_address}")
        logger.info(f"Connected to Ollama Service: {ollama_service_address}")
    
    def get_system_prompt(self, prompt_type: str = "personalize") -> str:
        """Fetch system prompt from Prompt Manager."""
        # Implement gRPC call to fetch prompt
       
        # Handle gRPC errors
        # Remove the below line and implement the method logic
        pass
    
    def call_gemini(self, user_query: str) -> Dict[str, Any]:
        """Call Gemini API."""
        result = {
            "model": self.gemini_model,
            "explanation": "",
            "success": False,
            "error_message": ""
        }
        
        if not self.gemini_client:
            result["error_message"] = "Gemini client not configured"
            return result
        
        try:
            logger.info("Calling Gemini API")
            messages = [{"role": "user", "content": user_query}]
            response = self.gemini_client.chat.completions.create(
                model=self.gemini_model,
                messages=messages
            )
            result["explanation"] = response.choices[0].message.content
            result["success"] = True
            logger.info("Gemini response received")
        except Exception as e:
            result["error_message"] = str(e)
            logger.error(f"Gemini error: {e}")
        
        return result
    
    # Implement call_ollama method
    def call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama Service via gRPC."""
        result = {
            "model": self.ollama_model,
            "explanation": "",
            "success": False,
            "error_message": ""
        }
        # Implement gRPC call to Ollama Service
                
        # Return suceess or failure result dict
          
        # Handle gRPC errors    
             
        return result
    
    def orchestrate_dual_explanation(self, concept: str) -> Dict[str, Any]:
        """
        Coordinate both Gemini and Ollama for dual response.
        
        Steps:
        1. Get system prompt
        2. Call Gemini
        3. Call Ollama
        4. Return combined results
        """
        logger.info(f"Processing dual explanation: {concept}")
        
        # Get system prompt
      
        # Construct user query
                
        # Call both models
      
        
        logger.info(f"Dual explanation completed for concept: {concept}")
        
        # return combined results
      
    
    def close(self):
        """Close all gRPC connections."""
        logger.info("Closing Orchestrator connections")
        # Close gRPC channels if open