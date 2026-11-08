from typing import Any
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def require_env(self,key : str,default : Any = None) -> Any:
        return os.getenv(key=key,default=default)
    
settings = Settings()
