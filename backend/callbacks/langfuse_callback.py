from langfuse.langchain import CallbackHandler
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class LangFuseCallBackHandler:
    """
    Wrapper around Langfuse's LangChain CallbackHandler.
    Reads credentials from environment variables or constructor arguments.
    """

    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        self.host = host or os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

    def get_callback_handler(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        trace_name: Optional[str] = None,
    ) -> Optional[CallbackHandler]:
        """
        Returns a configured Langfuse CallbackHandler for use in LangChain chains.
        Returns None if credentials are not configured.
        """
        if not self.public_key or not self.secret_key:
            print("[Langfuse] Warning: Missing public/secret key — observability disabled.")
            return None

        handler_kwargs: dict = {
            "public_key": self.public_key,
            "secret_key": self.secret_key,
            "host": self.host,
        }

        if session_id:
            handler_kwargs["session_id"] = session_id
        if user_id:
            handler_kwargs["user_id"] = user_id
        if trace_name:
            handler_kwargs["trace_name"] = trace_name

        try:
            handler = CallbackHandler(**handler_kwargs)
            return handler
        except Exception as e:
            print(f"[Langfuse] Failed to create callback handler: {e}")
            return None

    def flush(self) -> None:
        """Flush any pending Langfuse events. No-op if handler is not active."""
        pass


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_langfuse_manager: Optional[LangFuseCallBackHandler] = None


def get_langfuse_manager() -> LangFuseCallBackHandler:
    """Return (or lazily create) the global LangFuseCallBackHandler singleton."""
    global _langfuse_manager
    if _langfuse_manager is None:
        _langfuse_manager = LangFuseCallBackHandler()
    return _langfuse_manager


__all__ = ["LangFuseCallBackHandler", "get_langfuse_manager"]
