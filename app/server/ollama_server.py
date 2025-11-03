"""
Ollama gRPC Service - Minimal Implementation
============================================
Wraps Ollama HTTP API and exposes it via gRPC for microservices communication.
"""

import logging
from app.proto import ollama_service_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OllamaServiceServicer(ollama_service_pb2_grpc.OllamaServiceServicer):
    """Ollama gRPC Service Implementation."""
    
    def __init__(self, ollama_url="http://localhost:11434"):
        self.ollama_url = ollama_url
    
    # Implement the GenerateExplanation RPC method    
    def GenerateExplanation(self, request, context):
        """Generate explanation using Ollama."""
        # Call Ollama HTTP API
        
        # return the response
        
        # Handle exceptions and return failure response
        # Remove the below line and implement the method logic
        pass
 
def serve(port=50052):
    """Start the Ollama gRPC server."""
    # Step 1: Create a gRPC server with thread pool
    # max_workers=10 means it can handle 10 concurrent requests
  
    
    # Step 2: Register our service implementation with the server
   
    
    # Step 3: Bind to port 50052
    # [::]:50052 means listen on all network interfaces
   
    
    # Step 4: Start the server
    
    logger.info("=" * 60)
    logger.info("OLLAMA GRPC SERVICE STARTED")
    logger.info("=" * 60)
    logger.info(f"  Address: localhost:{port}")
    logger.info(f"  Ollama Backend: http://localhost:11434")
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to stop")
    
    # Step 5: Keep the server running until interrupted

if __name__ == '__main__':
    serve()

