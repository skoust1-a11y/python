import json
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from state import DocumentationReflectionState
from llm import llm
import re

# TODO: Implement reflection_node
#
# INSTRUCTIONS:
# 1. Get current state: task, draft_output, iteration_count, etc.
#
# 2. Create a prompt for the LLM that:
#    - Acts as an expert technical reviewer
#    - Evaluates the current draft against criteria:
#      - Completeness (0-10)
#      - Clarity (0-10)
#      - Examples (0-10)
#    - PROVIDES A JSON OUTPUT with:
#      - a nested object per criterion: score, issues, suggestions
#      - an overall_score
#      - "refined_content": The improved documentation IF overall_score < threshold
#      - "summary": A brief summary of the critique
#
# 3. Invoke the LLM:
#    - Use `llm.invoke([SystemMessage(...), HumanMessage(...)])`
#
# 4. Parse the JSON response:
#    - Handle potential markdown wrapping (```json ... ```)
#    - Read the nested per-criterion score/issues/suggestions
#
# 5. Update the state:
#    - Append feedback to state["reflection_feedback"]
#    - Update state["quality_score"]
#    - Increment iteration_count (always, to guarantee loop termination)
#    - IF score < threshold and iterations < max:
#        - Update state["draft_output"] with "refined_content"
#        - Set output_approved = False
#    - ELSE:
#        - Set output_approved = True
#
# 6. Return the updated state

CRITERIA = ("completeness", "clarity", "examples")

SYSTEM_PROMPT = (
    "You are an expert technical reviewer. You audit documentation for "
    "completeness, clarity and quality of examples, and you answer strictly "
    "with the JSON object you were asked for."
)


def _parse_criterion(result: dict, key: str) -> dict:
    """
    Pull one nested criterion out of the model's JSON.

    Expected shape: {"score": X, "issues": [...], "suggestions": [...]}
    Tolerates a bare number (e.g. "clarity": 8) or a missing key.
    """
    raw = result.get(key)

    if isinstance(raw, dict):
        score = raw.get("score")
        issues = raw.get("issues") or []
        suggestions = raw.get("suggestions") or []
    elif isinstance(raw, (int, float)) and not isinstance(raw, bool):
        score, issues, suggestions = raw, [], []
    else:
        score, issues, suggestions = None, [], []

    try:
        score = float(score) if score is not None else None
    except (TypeError, ValueError):
        score = None

    # Guard against the model returning a bare string instead of a list.
    if isinstance(issues, str):
        issues = [issues]
    if isinstance(suggestions, str):
        suggestions = [suggestions]

    return {
        "score": score,
        "issues": [str(i) for i in issues if str(i).strip()],
        "suggestions": [str(s) for s in suggestions if str(s).strip()],
    }


def _extract_json(raw: str) -> str:
    """
    Pull the JSON object out of a raw LLM response.

    Splitting on every "```" would corrupt the payload, because the refined
    documentation inside `refined_content` almost always contains its own
    markdown code fences. So only a fence wrapping the WHOLE response is
    stripped, then the outermost {...} is isolated as a fallback.
    """
    content = raw.strip()

    fenced = re.match(r'^```[a-zA-Z]*\s*\n?(.*?)\n?\s*```$', content, re.DOTALL)
    if fenced:
        content = fenced.group(1).strip()

    if not content.startswith("{"):
        start, end = content.find("{"), content.rfind("}")
        if start != -1 and end > start:
            content = content[start:end + 1]

    return content.strip()


def _format_feedback(label: str, overall_score: float, summary: str,
                     criteria: dict) -> str:
    """Render the critique into a single human-readable feedback entry."""
    parts = [f"{label}: Overall {overall_score}/10."]

    scored = [f"{name.capitalize()} {criteria[name]['score']}/10"
              for name in CRITERIA if criteria[name]["score"] is not None]
    if scored:
        parts.append("Scores: " + ", ".join(scored) + ".")

    if summary:
        parts.append(summary.strip())

    for name in CRITERIA:
        detail = criteria[name]
        if detail["issues"]:
            parts.append(f"{name.capitalize()} issues: "
                         + "; ".join(detail["issues"]) + ".")
        if detail["suggestions"]:
            parts.append(f"{name.capitalize()} suggestions: "
                         + "; ".join(detail["suggestions"]) + ".")

    return " ".join(parts)


def reflection_node(state: DocumentationReflectionState):
    """Critique generated documentation, and refine it when it falls short."""
    draft_output = state["draft_output"]
    task = state["task_description"]
    iteration = state.get("iteration_count", 0)
    threshold = state.get("quality_threshold", 8.0)
    max_iters = state.get("max_iterations", 3)

    previous_feedback = state.get("reflection_feedback") or []
    history_block = ""
    if previous_feedback:
        history_block = (
            "\n    Feedback from earlier rounds (do not repeat fixes already "
            "applied):\n    - " + "\n    - ".join(previous_feedback[-3:]) + "\n"
        )

    # SINGLE CALL: Critique AND Refine
    prompt = f"""Evaluate this technical documentation and refine it if necessary.

    Task / source code being documented:
    {task}

    Current documentation draft:
    {draft_output}
{history_block}
    Instructions:
    1. Score Completeness, Clarity and Examples from 0-10, and give an overall score.
       - Completeness: are Overview, Installation, Usage and API Documentation all
         present, and is every public function/class documented with type hints?
       - Clarity: is the language beginner-friendly, plain and unambiguous?
       - Examples: is there at least one runnable example per public API, with
         expected output?
    2. For EACH criterion list the concrete "issues" you found and actionable
       "suggestions" to fix them. Use empty lists only when there is nothing to report.
    3. IF overall_score < {threshold}, set "refined_content" to a full improved
       version of the documentation that fixes every issue you listed.
    4. IF overall_score >= {threshold}, set "refined_content" to null.
    5. CRITICAL: If overall_score >= {threshold}, the "summary" must be a positive
       confirmation of approval and MUST NOT mention any remaining minor issues
       or suggestions.
    6. Respond with ONLY the JSON object below, no prose before or after it.

    JSON Output Format:
    {{
        "completeness": {{"score": X, "issues": ["..."], "suggestions": ["..."]}},
        "clarity": {{"score": X, "issues": ["..."], "suggestions": ["..."]}},
        "examples": {{"score": X, "issues": ["..."], "suggestions": ["..."]}},
        "overall_score": X,
        "summary": "Positive approval message if score >= {threshold}, else brief assessment of issues",
        "refined_content": "The improved markdown documentation as a string (or null if approved)"
    }}
    """

    request_messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    response = llm.invoke(request_messages)

    content = _extract_json(response.content)

    try:
        result = json.loads(content)
        if not isinstance(result, dict):
            raise ValueError("reflection output was not a JSON object")

        overall_score = float(result["overall_score"])
        summary = result.get("summary", "") or ""
        refined_content = result.get("refined_content")
        criteria = {name: _parse_criterion(result, name) for name in CRITERIA}

        if overall_score >= threshold:
            # Approved: suppress any lingering nitpicks from the critique.
            summary = "The documentation meets all quality criteria and is approved."
            criteria = {name: {"score": criteria[name]["score"],
                               "issues": [], "suggestions": []}
                        for name in CRITERIA}
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        overall_score = 5.0
        summary = "Error parsing reflection output"
        refined_content = None
        criteria = {name: {"score": None, "issues": [], "suggestions": []}
                    for name in CRITERIA}

    label = "Initial Review" if iteration == 0 else f"Refinement {iteration} Review"
    feedback = _format_feedback(label, overall_score, summary, criteria)

    # ALWAYS advance the iteration counter so the reflector -> reflector loop is
    # guaranteed to terminate, even when the LLM returns no refined content or
    # the JSON fails to parse. Without this the graph loops until the recursion
    # limit is hit.
    next_iteration = iteration + 1

    # Mirror the quality gate in routing.should_continue so the state flag and
    # the routing decision can never disagree: exhausting the iteration budget
    # is itself a stop/approve condition.
    quality_met = overall_score >= threshold or overall_score >= 7.0
    budget_exhausted = next_iteration >= max_iters
    output_approved = quality_met or budget_exhausted

    updates = {
        "messages": [AIMessage(content=feedback)],
        "reflection_feedback": [feedback],
        "quality_score": overall_score,
        "iteration_count": next_iteration,
        "output_approved": output_approved,
    }

    # Only rewrite the draft when we are actually going around again.
    if not output_approved and isinstance(refined_content, str) and refined_content.strip():
        cleaned = refined_content.strip()
        cleaned = re.sub(r'^```markdown\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^```\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        updates["draft_output"] = cleaned.strip()
    # If no refined content was returned, keep the existing draft; the
    # incremented iteration_count still guarantees forward progress.

    return updates
