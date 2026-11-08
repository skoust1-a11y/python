from start.classifiers.intent_classifier import classify_chain
from langchain_core.runnables import RunnableLambda

def input_orchestrator(input_dict : dict) -> dict:
    classification = classify_chain.invoke({
        'query': input_dict['query']
    })
    chat_history = input_dict.get("chat_history", [])
    return {
        'classification' : classification,
        'original_query': input_dict["query"],
        'chat_history': chat_history
    }
orchestartor_LCEL = RunnableLambda(input_orchestrator)
