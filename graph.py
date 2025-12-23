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
    return {}


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
    return None
