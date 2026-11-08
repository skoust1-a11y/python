"""
Orchestrator Agent - Central Coordination Hub

Coordinates all AI services:
- Prompt Manager (gRPC)
- Ollama Service (gRPC)
- Gemini API (HTTP)
"""

import logging
from typing import Dict, Any, Optional

import grpc
from openai import OpenAI

from app.proto import (
    ollama_service_pb2,
    ollama_service_pb2_grpc,
    prompts_pb2,
    prompts_pb2_grpc,
)

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Coordinates all AI services and manages workflow."""

    DEFAULT_SYSTEM_PROMPT = (
        "You are a helpful AI tutor. Explain concepts clearly and use practical examples."
    )
    
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
        self.gemini_client = gemini_client
        self.gemini_model = gemini_model
        self.ollama_model = ollama_model
        
        # Write code to Connect to services
        self.prompt_channel = grpc.insecure_channel(prompt_manager_address)
        self.ollama_channel = grpc.insecure_channel(ollama_service_address)

        self.prompt_stub = prompts_pb2_grpc.PromptManagerStub(self.prompt_channel)
        self.ollama_stub = ollama_service_pb2_grpc.OllamaServiceStub(self.ollama_channel)
        
        # Once connected, log success messages
        logger.info(f"Connected to Prompt Manager: {prompt_manager_address}")
        logger.info(f"Connected to Ollama Service: {ollama_service_address}")
    
    def get_system_prompt(self, prompt_type: str = "personalize") -> str:
        """Fetch system prompt from Prompt Manager."""
        # Implement gRPC call to fetch prompt
        try:
            response = self.prompt_stub.GetPrompt(
                prompts_pb2.PromptRequest(prompt_name=prompt_type),
                timeout=5,
            )
            if response.found and response.prompt_text:
                return response.prompt_text
            logger.warning("Prompt lookup failed for '%s', using fallback", prompt_type)
            return self.DEFAULT_SYSTEM_PROMPT
        # Handle gRPC errors
        except grpc.RpcError as exc:
            logger.error("Prompt Manager gRPC error: %s", exc)
            return self.DEFAULT_SYSTEM_PROMPT
    
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
        try:
            response = self.ollama_stub.GenerateExplanation(
                ollama_service_pb2.GenerateRequest(
                    model=self.ollama_model,
                    prompt=prompt,
                ),
                timeout=120,
            )

            result["model"] = response.model or self.ollama_model
            result["explanation"] = response.explanation
            result["success"] = response.success
            result["error_message"] = response.error_message
        except grpc.RpcError as exc:
            result["error_message"] = f"{exc.code().name}: {exc.details()}"
            logger.error("Ollama gRPC error: %s", exc)
                
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
        system_prompt = self.get_system_prompt("personalize")
      
        # Construct user query
        user_query = (
            f"{system_prompt}\n\n"
            f"Concept: {concept}\n"
            "Provide a concise explanation suitable for a beginner."
        )
                
        # Call both models
        gemini_response = self.call_gemini(user_query)
        ollama_response = self.call_ollama(user_query)
      
        
        logger.info(f"Dual explanation completed for concept: {concept}")
        
        # return combined results
        return {
            "concept": concept,
            "gemini_response": gemini_response,
            "ollama_response": ollama_response,
        }
      
    
    def close(self):
        """Close all gRPC connections."""
        logger.info("Closing Orchestrator connections")
        # Close gRPC channels if open
        if hasattr(self, "prompt_channel"):
            self.prompt_channel.close()
        if hasattr(self, "ollama_channel"):
            self.ollama_channel.close()
