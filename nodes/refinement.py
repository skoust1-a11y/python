from langchain_core.messages import SystemMessage, HumanMessage
from state import DocumentationReflectionState
from llm import llm

# TODO: Implement refinement_node
# - Get current draft and latest feedback
# - Build refinement prompt with task, current docs, and critique
# - Generate improved documentation
# - Update draft_output and increment iteration_count

def refinement_node(state: DocumentationReflectionState):
    """Improve documentation based on critique."""
    # TODO: Implement refinement logic
    return state
