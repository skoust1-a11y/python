from __future__ import annotations

import time
from typing import Any, Dict, List, NamedTuple, Tuple

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger


class LLMError(Exception):
    pass


class Endpoint(NamedTuple):
    provider: str
    base_url: str
    api_key: str
    router: str
    agent: str


def resolve(provider: str = "") -> Endpoint:
    """Primary endpoint by default; pass a provider name for the fallback (LLM_* overrides apply to primary only)."""
    settings = get_settings()
    primary = not provider or provider == settings.llm_provider
    provider = provider or settings.llm_provider
    if provider == "ollama":
        key = (settings.llm_api_key.strip() if primary else "") or "ollama"
        model = (settings.llm_model_agent.strip() if primary else "") or settings.ollama_model
        router = (settings.llm_model_router.strip() if primary else "") or model
        return Endpoint(provider, settings.ollama_base_url, key, router, model)
    base, router, agent = settings.llm_catalog(provider)
    if primary and settings.llm_base_url.strip():
        base = settings.llm_base_url.strip()
    keys = {
        "openai": settings.openai_api_key or settings.llm_api_key,
        "grok": settings.xai_api_key,
        "gemini": settings.gemini_api_key,
        "groq": settings.groq_api_key,
    }
    return Endpoint(
        provider,
        base,
        keys[provider].strip(),
        (settings.llm_model_router.strip() if primary else "") or router,
        (settings.llm_model_agent.strip() if primary else "") or agent,
    )


def _usable(endpoint: Endpoint) -> bool:
    return endpoint.provider == "ollama" or bool(endpoint.api_key)


def _endpoints() -> List[Endpoint]:
    settings = get_settings()
    chain = [resolve()]
    fallback = settings.llm_fallback_provider
    if fallback and fallback != settings.llm_provider:
        chain.append(resolve(fallback))
    return [e for e in chain if _usable(e)]


def available() -> bool:
    return bool(_endpoints())


def complete(system: str, user: str, *, tier: str = "agent") -> Tuple[str, Dict[str, Any]]:
    """Try the primary provider, then LLM_FALLBACK_PROVIDER. Usage includes the model that answered."""
    chain = _endpoints()
    if not chain:
        raise LLMError("no_api_key")
    last: Exception = LLMError("llm_failed")
    for endpoint in chain:
        try:
            return _complete_one(endpoint, system, user, tier)
        except LLMError as exc:
            last = exc
    raise last


def _complete_one(endpoint: Endpoint, system: str, user: str, tier: str) -> Tuple[str, Dict[str, Any]]:
    settings = get_settings()
    model = endpoint.agent if tier == "agent" else endpoint.router
    url = endpoint.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "temperature": settings.llm_temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if "gpt-oss" in model:
        payload["reasoning_effort"] = "low"
    headers = {"Authorization": "Bearer " + endpoint.api_key, "Content-Type": "application/json"}
    last: Exception = LLMError("llm_failed")
    attempts = max(settings.llm_max_retries, 0) + 1
    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=settings.llm_timeout_s) as client:
                res = client.post(url, json=payload, headers=headers)
            if res.status_code == 429 and "insufficient_quota" in res.text:
                raise LLMError("insufficient_quota")
            if res.status_code == 429 or res.status_code >= 500:
                raise LLMError("http_{}".format(res.status_code))
            if res.status_code >= 400:
                raise LLMError("http_{}".format(res.status_code))
            data = res.json()
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            usage = data.get("usage") or {}
            return text, {
                "prompt": int(usage.get("prompt_tokens") or 0),
                "completion": int(usage.get("completion_tokens") or 0),
                "total": int(usage.get("total_tokens") or 0),
                "model": model,
            }
        except LLMError as exc:
            if str(exc) == "insufficient_quota" or str(exc).startswith("http_4"):
                raise
            last = exc
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            last = LLMError(str(exc))
        if attempt < attempts - 1:
            time.sleep(0.2 * (2 ** attempt))
    raise last


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed with the one configured model; [] on any failure so stored vectors never mix models."""
    settings = get_settings()
    key = settings.gemini_api_key.strip()
    if not texts or not key:
        return []
    model = "models/" + settings.embedding_model
    url = "https://generativelanguage.googleapis.com/v1beta/{}:batchEmbedContents".format(model)
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    vecs: List[List[float]] = []
    try:
        with httpx.Client(timeout=settings.llm_timeout_s) as client:
            for start in range(0, len(texts), 100):
                body = {
                    "requests": [
                        {
                            "model": model,
                            "content": {"parts": [{"text": text}]},
                            "outputDimensionality": settings.embedding_dim,
                        }
                        for text in texts[start : start + 100]
                    ]
                }
                res = client.post(url, json=body, headers=headers)
                if res.status_code >= 400:
                    get_logger("llm").warning("embed_failed", status=res.status_code, detail=res.text[:200])
                    return []
                vecs.extend(list(item.get("values") or []) for item in (res.json() or {}).get("embeddings") or [])
    except (httpx.HTTPError, TypeError, ValueError):
        return []
    ok = len(vecs) == len(texts) and all(len(vec) == settings.embedding_dim for vec in vecs)
    return vecs if ok else []
