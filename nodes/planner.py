import json
from langchain_core.messages import SystemMessage, HumanMessage
from state.state import MarketResearchState
from llm import llm
from llm import invoke_with_retry

def planning_node(state: MarketResearchState):
    """Generate a multi-step execution plan for market research.
    
    TODO:
    1. Extract user_request from state["messages"][0].content
    2. Build prompt asking LLM to decompose into 3-5 steps with JSON format
    3. Invoke llm.invoke() with SystemMessage and HumanMessage
    4. Parse JSON from response.content (remove markdown fences if present)
    5. Normalize plan items to dicts with step, action, tool, expected_output
    6. Limit to plan[:5]
    7. Update state["plan"], state["current_step"]=1, flags=False, replan_attempts=0
    8. Return state
    """
    # TODO: Step 1 - Extract request
    user_request = state['messages'][0].content
    # TODO: Step 2 - Build prompt
    planning_prompt = f"""Generate a 3-5 step plan to accomplish this request.

    Available tools:
    - search_web(query): Search DuckDuckGo for current information
    - calculate(expression): Perform mathematical calculations

    Output JSON format:
    [
    {{"step": 1, "action": "description", "tool": "tool_name", "expected_output": "expected result"}}
    ]

    Request: {user_request}

    Plan (JSON only):"""

    try:
        response = invoke_with_retry(
            llm,
            [
            SystemMessage(content="You are a planning assistant."),
            HumanMessage(content=planning_prompt)
        ]
        )
    except Exception as e:
        raise
    plan_text = response.content.strip()
    if "```json" in plan_text:
        plan_text = plan_text.split("```json")[1].split("```")[0].strip()
    elif "```" in plan_text:
        plan_text = plan_text.split("```")[1].split("```")[0].strip()
    try:
        plan = json.loads(plan_text)
        # Ensure plan is a list
        if not isinstance(plan, list):
            plan = [plan] if plan else []
    except json.JSONDecodeError as e:
        # Fallback: create a simple plan if parsing fails
        plan = [{
            "step": 1,
            "action": f"Search for information about: {user_request}",
            "tool": "search_web",
            "expected_output": "Relevant information found"
        }]

    # Normalize plan items to ensure required keys are present
    normalized_plan = []
    for idx, item in enumerate(plan):
        if not isinstance(item, dict):
            item = {}
        normalized_plan.append({
            "step": item.get("step", idx + 1),
            "action": item.get("action", f"Step {idx + 1}"),
            "tool": item.get("tool", "search_web"),
            "expected_output": item.get("expected_output", "N/A")
        })

    # Enforce maximum of 5 steps
    plan = normalized_plan[:5]

    state["plan"] = plan
    state["current_step"] = 1
    state["task_complete"] = False
    state["needs_replanning"] = False
    state["replan_attempts"] = 0  # Initialize replan attempts

    return state


    # TODO: Step 3 - Invoke LLM
    # TODO: Step 4 - Parse JSON
    # TODO: Step 5 - Normalize plan
    # TODO: Step 6 - Limit steps
    # TODO: Step 7 - Update state
    # TODO: Step 8 - Return state
