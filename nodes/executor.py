from langchain_core.messages import HumanMessage, ToolMessage
from state.state import MarketResearchState
from llm import llm_with_tools,invoke_with_retry
from tools.tools import search_web, calculate


def execution_node(state: MarketResearchState):
    """Execute the current step from the plan.
    
    TODO:
    1. Safety check: if no plan or current_step > len(plan), set task_complete=True, return
    2. Get step_info from state["plan"][current_step - 1], extract action, tool_name
    3. Create exec_message = f"Execute this step: {action} using {tool_name}"
    4. Invoke llm_with_tools.invoke(state["messages"] + [HumanMessage(content=exec_message)])
    5. Append response to state["messages"]
    6. If no response.tool_calls, append to execution_results and return
    7. Get tool_call from response.tool_calls[0], invoke search_web or calculate
    8. Append to execution_results: {"step": current_step, "action": action, "result": result}
    9. Append ToolMessage(content=result, tool_call_id=tool_call["id"]) to messages
    10. Return state
    """
    # TODO: Step 1 - Safety check
    if not state['plan'] or state["current_step"] < 1 or state["current_step"] > len(state['plan']):
        state["task_complete"] = True
        return state
    # TODO: Step 2 - Get step info
    current_step_num = state["current_step"]
    step_info = state["plan"][current_step_num - 1]
    # Guard against missing/malformed step_info fields
    action = step_info.get("action", f"Step {current_step_num}")
    tool_name = step_info.get("tool", "search_web")
    # TODO: Step 3 - Create message
    exec_message = f"Execute this step: {action} using {tool_name}"
    # TODO: Step 4 - Invoke LLM
    try:
        response = invoke_with_retry(
            llm_with_tools,
            state["messages"] + [HumanMessage(content=exec_message)]
        )
    except Exception as e:
        raise
    state["messages"].append(response)

    # Execute tool if called
    if response.tool_calls:
        tool_call = response.tool_calls[0]

        # Execute tool
        try:
            if tool_call["name"] == "search_web":
                result = search_web.invoke(tool_call["args"])
            elif tool_call["name"] == "calculate":
                result = calculate.invoke(tool_call["args"])
            else:
                result = f"Unknown tool: {tool_call['name']}"
        except Exception as e:
            result = f"Tool execution error: {str(e)}"

        # Store result
        state["execution_results"].append({
            "step": current_step_num,
            "action": action,
            "result": result
        })

        state["messages"].append(ToolMessage(
            content=result,
            tool_call_id=tool_call["id"]
        ))
    else:
        # No tool call - mark step as done with message
        state["execution_results"].append({
            "step": current_step_num,
            "action": action,
            "result": response.content or "Step completed without tool usage"
        })
    return state

    # TODO: Step 5 - Add response to messages
    # TODO: Step 6 - Handle no tool call
    # TODO: Step 7 - Execute tool
    # TODO: Step 8 - Store result
    # TODO: Step 9 - Add ToolMessage
    # TODO: Step 10 - Return state
