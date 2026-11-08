import json
from langchain_core.messages import SystemMessage, HumanMessage
from state.state import MarketResearchState
from llm import llm,invoke_with_retry


MAX_REPLAN_ATTEMPTS = 2  

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
    if not state["execution_results"]:
        state["task_complete"] = True
        return state
    
    if not state["plan"] or state["current_step"] < 1:
        state["task_complete"] = True
        return state
    
    if state["current_step"] > len(state["plan"]):
        state["task_complete"] = True
        return state

    current_step_num = state["current_step"]
    step_info = state["plan"][current_step_num - 1]
    last_result = state["execution_results"][-1]
    verification_prompt = f"""Verify if this step succeeded.

    Step: {step_info['action']}
    Expected: {step_info['expected_output']}
    Actual result: {last_result['result']}

    Evaluation criteria:
    - PASS if the result contains relevant information that addresses the step's goal, even if not perfect
    - PASS if search results mention the target company/entity, even if mixed with similar names
    - FAIL only if the result is completely irrelevant, empty, or clearly about a different entity
    - For ambiguous company names, be lenient - if results mention companies with similar names, consider it a partial PASS if some relevant information is present

    Evaluate and respond with JSON:
    {{"status": "PASS or FAIL", "reason": "explanation"}}
    """

    # TODO: Step 2 - Get info
    # TODO: Step 3 - Build prompt
    # TODO: Step 4 - Invoke LLM
    try:
        response = invoke_with_retry(llm, [
            SystemMessage(content="You are a verification assistant."),
            HumanMessage(content=verification_prompt)
        ])
    except Exception as e:
        raise

    # TODO: Step 5 - Parse result
    verification_text = response.content.strip()
    if "```json" in verification_text:
        verification_text = verification_text.split("```json")[1].split("```")[0].strip()
    elif "```" in verification_text:
        verification_text = verification_text.split("```")[1].split("```")[0].strip()

    try:
        verification = json.loads(verification_text)
    except json.JSONDecodeError as e:
        verification = {"status": "PASS", "reason": "Could not parse verification, assuming success"}

    state["verification_status"].append({
        "step": current_step_num,
        "status": verification["status"],
        "reason": verification["reason"]
    })
    if verification["status"] == "FAIL":
        if state.get("replan_attempts", 0) >= MAX_REPLAN_ATTEMPTS:
            state["task_complete"] = True
        else:
            state["needs_replanning"] = True
    else:
        state["replan_attempts"] = 0
        if current_step_num < len(state["plan"]):
            state["current_step"] += 1
        else:
            state["task_complete"] = True
    return state

