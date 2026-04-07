class MissingEnvVarError(Exception):
    """Custom exception for missing environment variables."""
    pass


class GibberishPromptError(Exception):
    """Raised when user input is too unclear to determine an emotion."""
    pass