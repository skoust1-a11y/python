from langfuse.langchain import CallbackHandler
from typing import Optional
import os 
from langfuse_callback import LangfuseCallbackManager
from dotenv import load_dotenv

load_dotenv()

class LangFuseCallBackHandler:
    def __init__(
            self,
            public_key : Optional[str] = None,
            secret_key : Optional[str] = None,
            host : Optional[str] = None,
            session_id  : Optional[str] = None,
            user_id : Optional[str] = None
            ):
        self.public_key = public_key or os.getenv('LANGFUSE_PUBLIC_KEY')
        self.secret_key = secret_key or os.getenv('LANGFUSE_PUBLIC_KEY')
        self.host = host or os.getenv('LANGFUSE_BASE_URL')


        def getup_callback_handler(
                self,
                session_id: Optional[str] = None,
                user_id: Optional[str] = None,
                trace_name: Optional[str] = None,
                ) -> Optional[CallbackHandler]:
            if not self.public_key or  not self.secret_key:
                return None
            effective_session_id = session_id or self.session_id
            effective_user_id = user_id or self.user_id
            os.environ["LANGFUSE_PUBLIC_KEY"] = self.public_key
            os.environ["LANGFUSE_SECRET_KEY"] = self.secret_key
            os.environ["LANGFUSE_HOST"] = self.host
            os.environ["LANGFUSE_BASE_URL"] = self.host
            try:
                langfuse_client = Langfuse(
                    public_key=self.public_key,
                    host=self.host,
                    secret_key=self.secret_key,
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

_get_langfuse_handler : Optional[CallbackHandler] = None

def get_LangFuse_Manager() -> LangfuseCallbackManager:
    global _get_langfuse_handler
    if _get_langfuse_handler is None:
        _get_langfuse_handler = LangFuseCallBackHandler()
    return _get_langfuse_handler



__all__=['LangFuseCallBackHandler','get_LangFuse_Manager']







