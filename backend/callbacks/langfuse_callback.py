from langfuse.langchain import CallbackHandler
from typing import Optional
import os
from dotenv import load_dotenv
from langfuse import Langfuse

load_dotenv()


LANGFUSE_BASE_URL = os.getenv("LANGFUSE_HOST")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")

if not LANGFUSE_BASE_URL:
    raise ValueError('The LangFuse Base Url Not Found in .env file')
if not LANGFUSE_PUBLIC_KEY:
    raise ValueError('The LangFuse Public Key Not Found in .env file')
if not LANGFUSE_SECRET_KEY:
    raise ValueError('The LangFuse Secre Key Not Found in .env file')
    


langfuse = Langfuse(
    base_url=LANGFUSE_BASE_URL,
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY
)


"""
Langfuse Callback Handler Module

This module provides a centralized Langfuse callback handler for tracing
LangChain chain executions in the Langfuse dashboard.
"""

## Task 2: Add Observability with Langfuse Callback Handler (Chat API)

class LangfuseCallbackManager:
    def __init__(
            self,
            public_key : Optional[str] = None,
            secret_key : Optional[str] = None,
            host : Optional[str] = None,
            session_id  : Optional[str] = None,
            user_id : Optional[str] = None
            ):
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        self.host = host or os.getenv("LANGFUSE_HOST")
    
    
    def get_callback_handler(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        trace_name: Optional[str] = None,
    ) -> Optional[CallbackHandler]:
        if not self.public_key or not self.secret_key:
            # Return None if credentials are not provided (optional observability)
            return None
        effective_session_id = session_id or self.session_id
        effective_user_id = user_id or self.user_id
        os.environ["LANGFUSE_PUBLIC_KEY"] = self.public_key
        os.environ["LANGFUSE_SECRET_KEY"] = self.secret_key
        os.environ["LANGFUSE_HOST"] = self.host
        os.environ["LANGFUSE_BASE_URL"] = self.host  # Set both for compatibility
        try:
            langfuse_client = Langfuse(
                secret_key=self.secret_key,
                host=self.host,
                public_key=self.public_key
            )
            try:
                langfuse_client.auth_check()
            except Exception:
                pass
        except Exception:
            langfuse_client = None
        
        handler_kwargs= {
            'public_key' : self.public_key,
            'update_trace' : True
        }
        try:
            if effective_session_id:
                handler_kwargs["session_id"] = effective_session_id
            if effective_user_id:
                handler_kwargs["user_id"] = effective_user_id
            if trace_name:
                handler_kwargs["trace_name"] = trace_name
            
            handler = CallbackHandler(**handler_kwargs)
        except TypeError as e:
            handler = CallbackHandler(
                public_key=self.public_key,
                update_trace=True
            )
        if langfuse_client and hasattr(handler, 'client'):
            handler._explicit_langfuse_client = langfuse_client
        
        if hasattr(handler, 'client'):
            handler._langfuse_client = handler.client
        
        return handler
    
    def flush(self):
        pass

_langfuse_manager : Optional[LangfuseCallbackManager] = None

def get_langfuse_manager() -> LangfuseCallbackManager:
    global _langfuse_manager
    if _langfuse_manager is None:
        _langfuse_manager = LangfuseCallbackManager()
    return _langfuse_manager

__all__ = ["LangfuseCallbackManager", "get_langfuse_manager"]









