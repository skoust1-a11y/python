# TODO: Implement should_continue function
#
# INSTRUCTIONS:
# 1. Check the state for:
#    - iteration_count
#    - max_iterations
#    - quality_score
#    - quality_threshold
#
# 2. Determine the path:
#    - IF iteration_count >= max_iterations: return "approve"
#    - IF quality_score >= quality_threshold: return "approve"
#    - IF quality_score is close to threshold (e.g. >= 7.0): return "approve"
#    - ELSE: return "refine"
#
# 3. When approving, mark output_approved = True in the state.

from state import DocumentationReflectionState

# Documentation is accepted when it lands within this distance of "good enough",
# even if it misses the configured threshold.
BORDERLINE_SCORE = 7.0


def _mark_approved(state: DocumentationReflectionState) -> None:
    """
    Record the approval on the state itself.

    A conditional-edge function cannot return state updates in LangGraph, so it
    writes the flag in place. Some LangGraph versions hand routers a read-only
    view of the state, hence the guard: `reflection_node` sets the same flag
    using identical logic, so the state is correct either way.
    """
    try:
        state["output_approved"] = True
    except (TypeError, AttributeError):  # read-only state view
        pass


def should_continue(state: DocumentationReflectionState) -> str:
    """Determine next step based on quality and iterations."""
    # Use .get() with defaults so a missing key can never raise a KeyError
    # mid-run (which would surface as an opaque 500 from the API).
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    quality_threshold = state.get("quality_threshold", 8.0)
    quality_score = state.get("quality_score", 0.0)

    # Hard stop first: the iteration budget always wins, otherwise the
    # reflector -> reflector edge can cycle forever.
    if iteration_count >= max_iterations:
        _mark_approved(state)
        return "approve"

    # Quality gate met.
    if quality_score >= quality_threshold:
        _mark_approved(state)
        return "approve"

    # Borderline: close enough to the threshold to accept.
    if quality_score >= BORDERLINE_SCORE:
        _mark_approved(state)
        return "approve"

    return "refine"
