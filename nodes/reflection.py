import json
from langchain_core.messages import SystemMessage, HumanMessage
from state import DocumentationReflectionState
from llm import llm

# TODO: Implement reflection_node
# 
# INSTRUCTIONS:
# 1. Get current state: task, draft_output, iteration_count, etc.
# 
# 2. Create a prompt for the LLM that:
#    - Acts as an expert technical reviewer
#    - Evaluates the current draft against criteria:
#      - Completeness (0-10)
#      - Clarity (0-10)
#      - Examples (0-10)
#    - PROVIDES A JSON OUTPUT with:
#      - scores for each criterion and an overall_score
#      - "refined_content": The improved documentation IF overall_score < threshold
#      - "summary": A brief summary of the critique
# 
# 3. Invoke the LLM:
#    - Use `llm.invoke([SystemMessage(...), HumanMessage(...)])`
# 
# 4. Parse the JSON response:
#    - Handle potential markdown wrapping (```json ... ```)
# 
# 5. Update the state:
#    - Append feedback to state["reflection_feedback"]
#    - Update state["quality_score"]
#    - IF score < threshold and iterations < max:
#        - Update state["draft_output"] with "refined_content"
#        - Increment iteration_count
#        - Set output_approved = False
#    - ELSE:
#        - Set output_approved = True
# 
# 6. Return the updated state

def reflection_node(state: DocumentationReflectionState):
    """Critique generated documentation."""
    # TODO: Implement reflection logic
    return state
