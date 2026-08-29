COMPLEX_KEYWORDS = [
    "500", "502", "503", "504", "error", "bug", "crash", "analyze",
    "failed", "failure", "deployment", "critical", "api", "exception",
    "traceback", "timeout", "latency", "stack trace", "outage", "debug",
    "incident", "fatal", "nullpointer", "memory leak", "segfault",
    "unhandled", "deadlock", "corrupted",
]

SIMPLE_KEYWORDS = [
    "billing", "invoice", "address", "update", "status", "account",
    "reset", "password", "subscription", "refund", "plan", "cancel",
    "receipt", "faq", "pricing", "profile", "login", "email",
    "payment", "downgrade", "upgrade",
]


def assess_complexity(description: str) -> str:
    """
    Heuristic-based routing for support tickets (no LLM, zero latency).

    Rules:
      1. Any complex keyword present            -> "complex"
      2. Any simple keyword present (no complex) -> "simple"
      3. Word count > 50                         -> "complex"
      4. Default                                 -> "simple"
    """
    if not description or not description.strip():
        return "simple"

    text = description.lower()
    word_count = len(text.split())

    # Rule 1: complex keyword triggers win outright
    if any(keyword in text for keyword in COMPLEX_KEYWORDS):
        return "complex"

    # Rule 2: no complex triggers, so a simple keyword forces the cheap tier
    if any(keyword in text for keyword in SIMPLE_KEYWORDS):
        return "simple"

    # Rule 3: long descriptions need more reasoning power
    if word_count > 50:
        return "complex"

    # Rule 4: default
    return "simple"
