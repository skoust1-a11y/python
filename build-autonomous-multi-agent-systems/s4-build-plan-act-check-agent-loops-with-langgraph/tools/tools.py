from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
import time
# TODO: Step 1 - Initialize DuckDuckGo search with timeout
# Hint: Use DuckDuckGoSearchRun with a timeout parameter (e.g., 10 seconds) to prevent hanging
# Store it in a variable like ddg_search
# Example: ddg_search = DuckDuckGoSearchRun(timeout=10)
ddg_search = DuckDuckGoSearchRun(timeout=10)

@tool
def search_web(query: str) -> str:
    """Search the web for current information using DuckDuckGo.
    
    TODO:
    1. Invoke ddg_search.invoke(query)
    2. Check if result is empty, return "No results found. Try a different search query."
    3. Handle exceptions, return error message
    4. Return the search result
    """
    start_time = time.time()
    # TODO: Step 1 - Invoke search
    try:
        result = ddg_search.invoke(query)
        elapsed = time.time() - start_time
        # DuckDuckGo returns text snippets
        if not result or len(result.strip()) == 0:
            return "No results found. Try a different search query."
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        return f"Search error: {str(e)}. Try rephrasing your query."
    # TODO: Step 2 - Check empty result
    # TODO: Step 3 - Handle exceptions
    # TODO: Step 4 - Return result


@tool
def calculate(expression: str) -> str:
    """Evaluate mathematical expressions.
    
    TODO:
    1. Evaluate expression using eval(expression, {"__builtins__": {}}, {})
    2. Format as "Result: {round(result, 2)}"
    3. Handle exceptions, return "Calculation error: {error}"
    4. Return formatted result
    """
    try:
        # Safe evaluation of mathematical expressions
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {round(result, 2)}"
    except Exception as e:
        return f"Calculation error: {str(e)}"
