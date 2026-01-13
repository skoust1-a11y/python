import json
from langchain_core.messages import SystemMessage, HumanMessage
from state.state import MarketResearchState
from llm import llm


def verification_node(state: MarketResearchState):
    """Verify if the executed step met success criteria.
    
    TODO:
    1. Safety: if no execution_results or current_step > len(plan), set task_complete=True, return
    2. Get step_info from plan[current_step-1], last_result from execution_results[-1]
    3. Build prompt with step action, expected_output, actual result, request JSON: {"status": "PASS"/"FAIL", "reason": "..."}
    4. Invoke llm.invoke() with SystemMessage and HumanMessage
    5. Parse JSON from response.content (remove markdown fences), handle JSONDecodeError
    6. Append to verification_status: {"step": current_step, "status": ..., "reason": ...}
    7. If status=="FAIL", set needs_replanning=True, return
    8. If PASS: reset replan_attempts=0, increment current_step or set task_complete=True
    9. Return state
    """
    # TODO: Step 1 - Safety checks
    # TODO: Step 2 - Get info
    # TODO: Step 3 - Build prompt
    # TODO: Step 4 - Invoke LLM
    # TODO: Step 5 - Parse result
    # TODO: Step 6 - Store status
    # TODO: Step 7 - Handle FAIL
    # TODO: Step 8 - Handle PASS
    # TODO: Step 9 - Return state
    
    raise NotImplementedError("This method is not yet implemented. Please complete the TODO steps above.")
