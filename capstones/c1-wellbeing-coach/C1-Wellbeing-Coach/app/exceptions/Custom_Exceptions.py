class MissingEnvVarError(Exception):
    """Custom exception for missing environment variables."""
    pass


class GibberishPromptError(Exception):
    """Raised when user input is too unclear to determine an emotion."""
    pass

class LlmCallException(Exception):
    """Raised when THERE is an issue with the LLM MODEL."""
    pass