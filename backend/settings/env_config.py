from typing import Optional,Any
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    variable : Optional[str] = None

    def require_env(self,key,value : Any = None) -> Any:
        return os.getenv(key=key,default=value)

config = Config()