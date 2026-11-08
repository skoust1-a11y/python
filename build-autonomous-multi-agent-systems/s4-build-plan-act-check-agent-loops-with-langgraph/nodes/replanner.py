import json
from langchain_core.messages import SystemMessage, HumanMessage
from state.state import MarketResearchState
from llm import llm,invoke_with_retry

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
    state["replan_attempts"] = state.get("replan_attempts", 0) + 1
    if state["replan_attempts"] > MAX_REPLANS:
        # Give up: stop looping and mark the task complete
        state["needs_replanning"] = False
        state["task_complete"] = True
        return state

    current_step_num = state["current_step"]
    failed_step = state["plan"][current_step_num - 1]
    verification_info = state["verification_status"][-1]

    # Get the actual execution result to provide context
    last_result = state["execution_results"][-1]["result"] if state["execution_results"] else "No result available"
    # Truncate if too long to avoid token limits
    result_preview = last_result[:1000] if len(last_result) > 1000 else last_result

    replanning_prompt = f"""Original plan failed at step {current_step_num}.

Original plan:
{json.dumps(state['plan'], indent=2)}

Failed step: {failed_step['action']}
Expected output: {failed_step.get('expected_output', 'N/A')}
Actual result: {result_preview}
Failure reason: {verification_info['reason']}

Generate a revised plan that addresses the failure. 

IMPORTANT GUIDELINES FOR SEARCH QUERIES:
- If the search returned results for the wrong company/entity, make the query MORE SPECIFIC
- Add company ticker symbols, exact company names in quotes, or additional distinguishing keywords
- For ambiguous company names, include industry, location, or other unique identifiers
- Example: Instead of "ACME Corp", try "ACME Corp ticker symbol" or "ACME Corp company financials exact name" or search for the specific ticker if known

For non-search steps, consider adding intermediate steps or using different tools.

Output the complete revised plan (all steps) as JSON:"""

    try:
        response = invoke_with_retry(llm, [
            SystemMessage(content="You are a replanning assistant."),
            HumanMessage(content=replanning_prompt)
        ])

    except Exception as e:
        raise
    revised_plan_text = response.content.strip()
    if "```json" in revised_plan_text:
        revised_plan_text = revised_plan_text.split("```json")[1].split("```")[0].strip()
    elif "```" in revised_plan_text:
        revised_plan_text = revised_plan_text.split("```")[1].split("```")[0].strip()

    try:
        revised_plan = json.loads(revised_plan_text)
        # Ensure plan is a list
        if not isinstance(revised_plan, list):
            revised_plan = [revised_plan] if revised_plan else state["plan"]
        state["plan"] = revised_plan
        # Note: current_step is NOT reset - we retry the same step number with the revised plan
        # This matches the sprint master's approach
    except json.JSONDecodeError as e:
        # If replanning fails, mark as complete to avoid infinite loop
        state["task_complete"] = True

    state["needs_replanning"] = False
    return state

    # TODO: Step 2 - Check max attempts
    # TODO: Step 3 - Get context
    # TODO: Step 4 - Build prompt
    # TODO: Step 5 - Invoke LLM
    # TODO: Step 6 - Parse plan
    # TODO: Step 7 - Normalize plan
    # TODO: Step 8 - Update state
    # TODO: Step 9 - Handle error
    # TODO: Step 10 - Return state
    
