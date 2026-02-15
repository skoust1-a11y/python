def assess_complexity(description: str) -> str:
    """
    TASK 1: Implement heuristic-based routing for support tickets.
    
    Heuristic Rules:
    1. Check for Complex Keywords:
       If the description contains words like '500', 'error', 'bug', 'crash', 
       'analyze', 'failed', 'deployment', 'critical', 'api', etc.
       -> Return "complex"
       
    2. Check for Simple Keywords:
       If the description contains words like 'billing', 'invoice', 
       'address', 'update', 'status', 'account', 'reset', etc.
       -> Return "simple"
       
    3. Length Metric:
       If the word count of the description is > 50 words.
       -> Return "complex"
       
    Default: Return "simple"
    """
    
    # TODO: Implement the heuristic logic here
    # 1. Lowercase the content
    # 2. Define keyword lists
    # 3. Apply the rules
    
    return 
