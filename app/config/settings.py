import os
from typing import Any, Dict

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env file into environment variables
load_dotenv()


class Settings(BaseSettings):
    # Keep specific fields for type safety (optional, but good for critical ones)
    app_name: str = "Wellbeing Coach"
    debug: bool = False

    model_config = {
        "env_file": ".env",   # Still specify for Pydantic to read
        "extra": "ignore",    # Ignore extras since we're handling them separately
    }

    @property
    def all_env_vars(self) -> Dict[str, Any]:
        """Returns all environment variables as a dict for easy access."""
        return dict(os.environ)

    def get_env(self, key: str, default: Any = None) -> Any:
        """Get any environment variable by key, with optional default."""
        return os.getenv(key, default)


# Global settings instance
settings = Settings()
