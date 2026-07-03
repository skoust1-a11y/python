"""Shared token counting utilities."""

import tiktoken

_encoding_cache = None


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    if not text:
        return 0
    global _encoding_cache
    if _encoding_cache is None:
        try:
            _encoding_cache = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _encoding_cache = False

    if _encoding_cache is False:
        return max(1, len(text) // 4)
    return len(_encoding_cache.encode(text))
