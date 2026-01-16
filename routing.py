# TODO: Implement should_continue function
# Logic:
# - If iteration_count >= max_iterations: approve
# - If quality_score >= quality_threshold: approve
# - If 7.0 <= quality_score < quality_threshold: approve (borderline)
# - Otherwise: return "refine"

from state import DocumentationReflectionState


def should_continue(state: DocumentationReflectionState) -> str:
    """Determine next step based on quality and iterations."""
    # TODO: Implement routing logic
    return "refine"
