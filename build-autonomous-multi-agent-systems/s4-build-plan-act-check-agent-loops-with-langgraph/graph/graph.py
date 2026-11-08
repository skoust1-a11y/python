from langgraph.graph import StateGraph, END
from state.state import MarketResearchState
from nodes.planner import planning_node
from nodes.executor import execution_node
from nodes.verifier import verification_node
from nodes.replanner import replanning_node


MAX_STEPS = 10  # Safety limit for total execution steps


def should_continue(state: MarketResearchState) -> str:
    """Route based on state to determine next action.
    
    TODO:
    1. If task_complete is True, return "complete"
    2. If current_step > MAX_STEPS, set task_complete=True, return "complete"
    3. If needs_replanning is True, return "replan"
    4. Return "execute"
    """
    # TODO: Step 1 - Check complete
    # TODO: Step 2 - Check max steps
    # TODO: Step 3 - Check replanning
    # TODO: Step 4 - Return execute
    if state["task_complete"]:
        return "complete"
    
    # Safety check: prevent infinite loops by limiting total execution steps
    execution_count = len(state.get("execution_results", []))
    if execution_count >= MAX_STEPS:
        state["task_complete"] = True
        return "complete"
    
    # Safety check for invalid current_step or empty plan
    if not state["plan"] or state["current_step"] < 1:
        state["task_complete"] = True
        return "complete"
    
    if state["current_step"] > len(state["plan"]):
        state["task_complete"] = True
        return "complete"
    
    if state["needs_replanning"]:
        return "replan"
    else:
        return "execute"


# TODO: Step 1 - Create workflow = StateGraph(MarketResearchState)
# TODO: Step 2 - Add nodes: planner, executor, verifier, replanner
# TODO: Step 3 - Set entry point: "planner"
# TODO: Step 4 - Add edges: planner->executor, executor->verifier, replanner->executor
# TODO: Step 5 - Add conditional edges from verifier with should_continue, mapping: {"execute": "executor", "replan": "replanner", "complete": END}
# TODO: Step 6 - Compile: app_graph = workflow.compile()




workflow = StateGraph(MarketResearchState)

# Add nodes
workflow.add_node("planner", planning_node)
workflow.add_node("executor", execution_node)
workflow.add_node("verifier", verification_node)
workflow.add_node("replanner", replanning_node)

# Define edges
workflow.set_entry_point("planner")
workflow.add_edge("planner", "executor")
workflow.add_edge("executor", "verifier")

# Conditional routing from verifier
workflow.add_conditional_edges(
    "verifier",
    should_continue,
    {
        "execute": "executor",
        "replan": "replanner",
        "complete": END
    }
)

workflow.add_edge("replanner", "executor")

# Compile
app_graph = workflow.compile()

