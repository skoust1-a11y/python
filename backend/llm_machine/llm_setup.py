from langchain_openai import ChatOpenAI
from settings.env_config import config
from langchain_groq import ChatGroq

if not config.require_env('GEMINI_API_KEY'):
    raise ValueError('LLM API KEY NOT FOUND')




llm_url = config.require_env('GEMINI_BASE_URL','https://generativelanguage.googleapis.com/v1beta/openai/')
model = config.require_env('GEMINI_MODEL_NAME','gemini-2.5-flash')
api_key = config.require_env('GEMINI_API_KEY')





# llm = ChatOpenAI(
#     api_key=api_key,
#     base_url=llm_url,
#     model=model,
#     max_retries=3,
#     temperature=0.1
# )


llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    api_key='***REMOVED***',
    max_retries=3
)