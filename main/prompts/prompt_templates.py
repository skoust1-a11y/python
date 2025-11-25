"""
Prompt templates for RAG query pipeline.

TODO: Complete the implementation of create_production_prompt() function.
This function creates a production-ready prompt template with hallucination prevention.
"""

# TODO: Import necessary modules
# Verify these imports are correct for your implementation:
from langchain_core.prompts import ChatPromptTemplate
from ..config import logger


def create_production_prompt() -> ChatPromptTemplate:
    """
    Create a production-ready RAG prompt template that:
    - Combines system instructions, retrieved context, and user questions
    - Explicitly prevents hallucinations
    - Handles cases where context is insufficient
    
    This function creates a ChatPromptTemplate with two message roles:
    1. System message: Contains instructions for the LLM and a placeholder for context
    2. Human message: Contains a placeholder for the user's question
    
    Returns:
        ChatPromptTemplate instance with hallucination prevention instructions
        
    Hints:
        1. Log that you're creating the production prompt template
        2. Use ChatPromptTemplate.from_messages() to create the template
        3. Pass a list of tuples, where each tuple contains:
           - Role name: "system" or "human"
           - Message content: String with placeholders like {context} and {question}
        4. System message should include:
           - Introduction: "You are AutoMind Motors' technical support assistant..."
           - CRITICAL INSTRUCTIONS section with:
             * Answer ONLY using provided context
             * Fallback message for insufficient information
             * No assumptions or external knowledge
             * Source citation requirements
             * Technical precision guidance
             * Multiple source synthesis
             * Safety-critical question handling
           - Context placeholder: "Context:\n{context}"
        5. Human message should contain: "{question}"
        6. Log successful template creation
        7. Return the template
    """
    # TODO: Step 1 - Log that you're creating the production prompt template
    
    # TODO: Step 2 - Create ChatPromptTemplate using from_messages()
    # Use ChatPromptTemplate.from_messages() with a list of message tuples
    # Each tuple should be: (role, message_content)
    
    # TODO: Step 3 - Define system message
    # Create system message with:
    #   - Introduction: "You are AutoMind Motors' technical support assistant. You help customers with vehicle maintenance, troubleshooting, and technical questions."
    #   - CRITICAL INSTRUCTIONS section:
    #     * "Answer ONLY using the provided context below"
    #     * Fallback message: "If the context doesn't contain enough information to answer the question, respond: 'I don't have enough information in the knowledge base to answer this question accurately. Please contact AutoMind Motors support at support@automind.com or call 1-800-AUTO-MIND.'"
    #     * "Never make assumptions or use external knowledge not present in the context"
    #     * "Always cite the source document when providing answers (use the [Source: ...] tags from context)"
    #     * "Be precise and technical when context allows"
    #     * "If multiple sources provide relevant information, synthesize them coherently"
    #     * "For safety-critical questions, be extra cautious and recommend professional inspection if uncertain"
    #   - Context placeholder: "Context:\n{context}"
    
    # TODO: Step 4 - Define human message
    # Create human message with: "{question}"
    
    # TODO: Step 5 - Combine messages in from_messages()
    # Pass list of tuples: [("system", system_message), ("human", human_message)]
    
    # TODO: Step 6 - Log successful template creation
    
    # TODO: Step 7 - Return the template
    
    # Placeholder - remove this line once you implement the function
    raise NotImplementedError("TODO: Implement create_production_prompt() function")

