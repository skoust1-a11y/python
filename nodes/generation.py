from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from state import DocumentationReflectionState
from llm import llm
import re

# TODO: Implement generation_node
#
# INSTRUCTIONS:
# 1. Get the task description from state["task_description"]
#
# 2. Create a prompt for the LLM that:
#    - Acts as an expert technical writer
#    - Asks to generate a README.md for the provided Python code
#    - Requires sections: Overview, Installation, Usage, API Documentation
#    - Uses beginner-friendly language
#    - Enforces markdown format
#
# 3. Invoke the LLM:
#    - Use `llm.invoke([SystemMessage(...), HumanMessage(...)])`
#
# 4. Process the response:
#    - Extract the content
#    - Clean up any markdown code blocks if necessary (e.g. remove ```markdown ... ```)
#
# 5. Connect to the graph:
#    - Update state["draft_output"] with the generated documentation
#    - Initialize state["iteration_count"] to 0 (or reset it)
#    - Set state["output_approved"] to False
#    - Propagate state["messages"] and state["reflection_feedback"]
#
# 6. Return the updated state

SYSTEM_PROMPT = (
    "You are an expert technical writer who specialises in documentation for "
    "beginners. You explain Python code in plain, approachable language without "
    "sacrificing technical accuracy."
)


def generation_node(state: DocumentationReflectionState):
    """Generate initial technical documentation."""
    task = state["task_description"]

    prompt = f"""Generate a README.md (markdown) file documenting the provided Python code.

    Python code / task:
    {task}

    Required sections (use these as top-level markdown headings):
    - Overview
    - Installation
    - Usage
    - API Documentation (include type hints for every public function and class)

    AUDIENCE AND LANGUAGE:
    - Write for a beginner who is new to this codebase and may be new to Python.
    - Use beginner-friendly language: short sentences, plain words, and the
      active voice. Avoid unexplained jargon; when a technical term is
      unavoidable, define it in one short clause the first time it appears.
    - Explain *why* something is done, not only *what* the code does.
    - Include at least one copy-pasteable, runnable example per public API,
      showing both the command/call and its expected output.

    CRITICAL RULE: Output only the markdown document, with no surrounding
    commentary and no wrapping code fences.
    """

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    response = llm.invoke(messages)

    result = response.content.strip()

    # Strip markdown code fences the model may have wrapped the document in.
    cleaned = re.sub(r'^```markdown\s*', '', result, flags=re.IGNORECASE)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    cleaned = cleaned.strip()

    # `messages` and `reflection_feedback` use operator.add reducers, so the
    # lists below are appended to whatever is already in the state. Returning
    # them keeps the full conversation history and the feedback log in the
    # state instead of dropping them on this hop.
    return {
        "messages": [
            HumanMessage(content=f"Generate documentation for:\n{task}"),
            AIMessage(content=cleaned),
        ],
        "draft_output": cleaned,
        "reflection_feedback": [],
        "iteration_count": 0,
        "quality_score": 0.0,
        "output_approved": False,
    }
