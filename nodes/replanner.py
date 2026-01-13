import json
from langchain_core.messages import SystemMessage, HumanMessage
from state.state import MarketResearchState
from llm import llm

MAX_REPLANS = 2


def replanning_node(state: MarketResearchState):
    """Generate an adjusted plan when a step fails verification.
    
    TODO:
    1. Increment state["replan_attempts"]
    2. If replan_attempts > MAX_REPLANS, set needs_replanning=False, advance/complete, return
    3. Get failed_step from plan[current_step-1], verification_info from verification_status[-1]
    4. Build prompt with original plan (json.dumps), failed step details, failure reason, execution result[:500]
    5. Invoke llm.invoke() with SystemMessage and HumanMessage
    6. Parse JSON from response.content (remove markdown fences)
    7. Normalize revised_plan items to dicts with step, action, tool, expected_output
    8. Set state["plan"] = normalized_plan[:5], state["needs_replanning"] = False
    9. Handle JSONDecodeError: simplify failed step action, set needs_replanning=False
    10. Return state
    """
    # TODO: Step 1 - Increment attempts
    # TODO: Step 2 - Check max attempts
    # TODO: Step 3 - Get context
    # TODO: Step 4 - Build prompt
    # TODO: Step 5 - Invoke LLM
    # TODO: Step 6 - Parse plan
    # TODO: Step 7 - Normalize plan
    # TODO: Step 8 - Update state
    # TODO: Step 9 - Handle error
    # TODO: Step 10 - Return state
    
    raise NotImplementedError("This method is not yet implemented. Please complete the TODO steps above.")
