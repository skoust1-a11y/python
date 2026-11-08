"""LLM prompt templates for legal document analysis."""

from app.prompts.manager import PromptManager
from app.prompts.types import DEFAULT_RESPONSE_MODE, RESPONSE_MODES, ResponseMode

__all__ = [
    "DEFAULT_RESPONSE_MODE",
    "RESPONSE_MODES",
    "PromptManager",
    "ResponseMode",
]
