from fastapi import APIRouter
from langchain_core.runnables import RunnableWithMessageHistory
from start.orchestrators.estate_orchestrator import orchestartor_LCEL
# from chat_history.inMemory import get_session_history
from start.chat_history.inMemory import get_session_history
from langchain.agents import create_agent
from start.bots.location import location_agent_runnbale 
router = APIRouter()

full_chain = orchestartor_LCEL | branchDecider # we will branch plz wait




stateful_chain = RunnableWithMessageHistory(
    runnable=full_chain,
    get_session_history=get_session_history,
    input_messages_key='query',
    history_messages_key='chat_history'
)


# @router.get('/check')
# def check():
#     response = location_agent_runnbale.invoke({
#         'original_query':'I am in Hyderabad,Telangana'
#     })
#     return response