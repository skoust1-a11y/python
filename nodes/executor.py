from langchain_core.messages import HumanMessage, ToolMessage
from state.state import MarketResearchState
from llm import llm_with_tools
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
    # TODO: Step 2 - Get step info
    # TODO: Step 3 - Create message
    # TODO: Step 4 - Invoke LLM
    # TODO: Step 5 - Add response to messages
    # TODO: Step 6 - Handle no tool call
    # TODO: Step 7 - Execute tool
    # TODO: Step 8 - Store result
    # TODO: Step 9 - Add ToolMessage
    # TODO: Step 10 - Return state
    
    raise NotImplementedError("This method is not yet implemented. Please complete the TODO steps above.")
