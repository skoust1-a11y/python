from langgraph.graph import StateGraph, END
from state import DocumentationReflectionState
from nodes.generation import generation_node
from nodes.reflection import reflection_node
from nodes.refinement import refinement_node
from routing import should_continue

# TODO: Build the reflection graph
# - Create StateGraph with DocumentationReflectionState
# - Add nodes: generator, reflector, refiner
# - Set entry point: generator
# - Add edge: generator → reflector
# - Add conditional edge: reflector → (refine or approve)
# - Add edge: refiner → reflector (loop back)
# - Compile and return

def build_graph():
    """Build and compile the documentation reflection graph."""
    # TODO: Implement graph building
    return None
