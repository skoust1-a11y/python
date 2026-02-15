from langchain_core.messages import HumanMessage, SystemMessage
from state import DocumentationReflectionState
from llm import llm

# TODO: Implement generation_node
# 
# INSTRUCTIONS:
# 1. Get the task description from state["task_description"]
# 
# 2. Create a prompt for the LLM that:
#    - Acts as an expert technical writer
#    - Asks to generate a README.md for the provided Python code
#    - Requires sections: Overview, Installation, Usage, API Documentation
#    - Enforces markdown format
# 
# 3. Invoke the LLM:
#    - Use `llm.invoke([SystemMessage(...), HumanMessage(...)])`
# 
# 4. Process the response:
#    - Extract the content
#    - Clean up any markdown code blocks if necessary (e.g. remove ```markdown ... ```)
# 
# 5. Connect to the graph:
#    - Update state["draft_output"] with the generated documentation
#    - Initialize state["iteration_count"] to 0 (or reset it)
#    - Set state["output_approved"] to False
# 
# 6. Return the updated state

def generation_node(state: DocumentationReflectionState):
    """Generate initial technical documentation."""
    # TODO: Implement generation logic
    return state
