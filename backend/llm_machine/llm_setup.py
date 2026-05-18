from langchain_openai import ChatOpenAI
from settings.env_config import config

if not config.require_env('GEMINI_API_KEY'):
    raise ValueError('LLM API KEY NOT FOUND')




llm_url = config.require_env('GEMINI_BASE_URL','https://generativelanguage.googleapis.com/v1beta/openai/')
model = config.require_env('GEMINI_MODEL_NAME','gemini-2.5-flash-lite')
api_key = config.require_env('GEMINI_API_KEY')





llm = ChatOpenAI(
    api_key=api_key,
    base_url=llm_url,
    model=model,
    max_retries=3,
    temperature=0.1
)