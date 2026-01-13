import json
from langchain_core.messages import SystemMessage, HumanMessage
from state.state import MarketResearchState
from llm import llm


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
    # TODO: Step 2 - Build prompt
    # TODO: Step 3 - Invoke LLM
    # TODO: Step 4 - Parse JSON
    # TODO: Step 5 - Normalize plan
    # TODO: Step 6 - Limit steps
    # TODO: Step 7 - Update state
    # TODO: Step 8 - Return state
    
    raise NotImplementedError("This method is not yet implemented. Please complete the TODO steps above.")
