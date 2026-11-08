"""Application-wide exception hierarchy."""


class AppError(Exception):
    """Base error for expected application failures."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        issues: list[dict] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.issues = issues or []
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code


class ConfigurationError(AppError):
    """Invalid or incomplete environment configuration."""

    status_code = 500
    error_code = "configuration_error"


class ProviderError(AppError):
    """Failure talking to an external provider adapter."""

    status_code = 502
    error_code = "provider_error"


class ProviderNotImplementedError(ProviderError):
    """Requested provider adapter is not wired yet."""

    status_code = 501
    error_code = "provider_not_implemented"


class NotFoundError(AppError):
    """Requested resource does not exist."""

    status_code = 404
    error_code = "not_found"


class ConflictError(AppError):
    """The request conflicts with the current resource state."""

    status_code = 409
    error_code = "conflict"


class PortfolioUploadError(AppError):
    """Uploaded portfolio file failed structural validation."""

    status_code = 400
    error_code = "portfolio_upload_error"


class PortfolioImportError(ConflictError):
    """A staged portfolio cannot be imported in its current state."""

    error_code = "portfolio_import_error"


class AgentError(AppError):
    """An investment-analysis agent failed during execution."""

    status_code = 500
    error_code = "agent_error"
