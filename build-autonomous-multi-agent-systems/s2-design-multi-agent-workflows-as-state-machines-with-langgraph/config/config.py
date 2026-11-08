import os

try:
    from dotenv import load_dotenv
except ImportError:  
    def load_dotenv() -> bool:
        return False


load_dotenv()


REQUIRED_ENV_VARS = [
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_LLM_DEPLOYMENT",
]


def _validate_required_env_vars() -> None:
    missing = []
    for name in REQUIRED_ENV_VARS:
        value = os.getenv(name)
        if value is None or not str(value).strip():
            missing.append(name)

    if missing:
        raise ValueError(
            "Missing required environment configuration: " + ", ".join(missing)
        )


_validate_required_env_vars()


config = {
    "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "azure_api_key": os.getenv("AZURE_OPENAI_API_KEY"),
    "azure_embedding_deployment": os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
    "azure_llm_deployment": os.getenv("AZURE_OPENAI_LLM_DEPLOYMENT"),
    "azure_llm_model": os.getenv("AZURE_OPENAI_LLM_MODEL", "gpt-4o"),
    "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
}


