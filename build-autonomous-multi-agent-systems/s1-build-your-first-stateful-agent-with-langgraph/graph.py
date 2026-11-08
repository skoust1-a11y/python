"""Graph nodes and building logic for the support agent with checkpointing."""

from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage
from schemas import SupportAgentState


def greeting_node(state: SupportAgentState) -> dict:
    """
    Ask for user's name - sends initial greeting if this is the first interaction.
    
    TODO:
    1. If user_name exists, return {}
    2. Return messages: [AIMessage("Hi! What's your name?")] and conversation_stage: "greeting"
    """
    # TODO: Implement greeting_node logic
    if state.get("user_name"):
        return {}

    return {
        "messages": [AIMessage("Hi! What's your name?")],
        "conversation_stage": "greeting"
    }





def identify_issue_node(state: SupportAgentState) -> dict:
    """
    Extract user name and ask for issue.
    
    TODO:
    1. Extract name from last HumanMessage if user_name missing
    2. If name extracted, return user_name, messages, conversation_stage: "identifying"
    3. If user_name exists but issue_type missing and last message is AI, ask for issue
    4. Otherwise return {}
    """
    # TODO: Implement identify_issue_node logic
    messages = state.get("messages", [])

    # 1. If user_name is missing, extract it from the last HumanMessage
    if not state.get("user_name"):
        last_human = next(
            (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
        )
        if last_human is not None:
            name = last_human.content.strip()
            return {
                "user_name": name,
                "messages": [
                    AIMessage(f"Thanks, {name}! What issue can I help you with?")
                ],
                "conversation_stage": "identifying",
            }

    # 3. user_name exists but issue_type missing and last message is AI -> ask for issue
    elif not state.get("issue_type") and messages and isinstance(messages[-1], AIMessage):
        return {
            "messages": [AIMessage("What issue can I help you with?")],
            "conversation_stage": "identifying",
        }

    # 4. Otherwise
    return {}


def resolve_node(state: SupportAgentState) -> dict:
    """
    Identify issue type and provide acknowledgment.
    
    TODO:
    1. If issue_type missing, get last HumanMessage
    2. Identify issue: "order" if "order" in content, "refund" if "refund" in content, else "other"
    3. Return issue_type, messages, conversation_stage: "resolved"
    4. Otherwise return {}
    """
    # TODO: Implement resolve_node logic
    if not state.get("issue_type"):
        messages = state.get("messages", [])
        last_human = next(
            (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
        )
        content = last_human.content.lower() if last_human else ""

        if "order" in content:
            issue_type = "order"
        elif "refund" in content:
            issue_type = "refund"
        else:
            issue_type = "other"

        return {
            "issue_type": issue_type,
            "messages": [
                AIMessage(
                    f"Got it — I've logged your {issue_type} issue and our team will help you resolve it."
                )
            ],
            "conversation_stage": "resolved",
        }

    return {}


def build_graph(checkpointer=None):
    """
    Build and compile the support agent graph.
    
    TODO:
    1. Create StateGraph with SupportAgentState
    2. Add nodes: "greeting", "identify_issue", "resolve"
    3. Add edges: greeting -> identify_issue -> resolve
    4. Set entry point: "greeting"
    5. Set finish point: "resolve"
    6. Use MemorySaver if checkpointer is None
    7. Compile and return graph
    """
    # TODO: Implement build_graph function
    graph = StateGraph(SupportAgentState)

    graph.add_node("greeting", greeting_node)
    graph.add_node("identify_issue", identify_issue_node)
    graph.add_node("resolve", resolve_node)

    graph.add_edge("greeting", "identify_issue")
    graph.add_edge("identify_issue", "resolve")

    graph.set_entry_point("greeting")
    graph.set_finish_point("resolve")

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)
