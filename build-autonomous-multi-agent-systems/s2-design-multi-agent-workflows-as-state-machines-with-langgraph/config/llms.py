
from langchain_openai.llms.azure import AzureOpenAI
from ..config.config import config


_llm = None

REQUIRED_LLM_CONFIG = (
    "azure_endpoint",
    "azure_api_key",
    "api_version",
    "azure_llm_deployment",
)


def get_llm():
    global _llm

    if _llm is None:
        missing = [
            key for key in REQUIRED_LLM_CONFIG
            if not str(config.get(key) or "").strip()
        ]
        if missing:
            raise ValueError(
                "Cannot create AzureOpenAI LLM, missing configuration: "
                + ", ".join(missing)
            )

        _llm = AzureOpenAI(
            azure_endpoint=config.get("azure_endpoint"),
            api_key=config.get("azure_api_key"),
            api_version=config.get("api_version"),
            deployment_name=config.get("azure_llm_deployment"),
            model=config.get("azure_llm_model", "gpt-4o"),
            temperature=0.1,
            max_tokens=50,
            max_retries=5,
        )
    return _llm

