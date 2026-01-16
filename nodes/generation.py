from langchain_core.messages import HumanMessage, SystemMessage
from state import DocumentationReflectionState
from llm import llm

# TODO: Implement generation_node
# - Takes Python code from task_description
# - Generates initial documentation (README.md format)
# - Include: overview, installation, usage examples, API docs
# - Use beginner-friendly language and markdown
# - Store in draft_output, initialize iteration_count to 0
def generation_node(state: DocumentationReflectionState):
    """Generate initial technical documentation."""
    # TODO: Implement generation logic
    return state
