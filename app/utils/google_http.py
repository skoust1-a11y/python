"""HTTP/SSL helpers for outbound API clients (Google GenAI, httpx, LlamaIndex LLMs)."""

from __future__ import annotations

import os
import ssl
from typing import Any

import httpx


def build_ssl_context() -> ssl.SSLContext:
    """Build an SSL context that prefers the OS trust store on Windows.

    httpx and several SDKs default to certifi's CA bundle, which often fails when
    a custom root CA is installed in the OS trust store (proxy/VPN/antivirus).
    """
    cert_file = os.environ.get("SSL_CERT_FILE", "").strip()
    cert_dir = os.environ.get("SSL_CERT_DIR", "").strip()
    if cert_file or cert_dir:
        return ssl.create_default_context(
            cafile=cert_file or None,
            capath=cert_dir or None,
        )
    return ssl.create_default_context()


def build_httpx_clients() -> dict[str, httpx.Client | httpx.AsyncClient]:
    """Return sync/async httpx clients using the shared SSL context."""
    verify = build_ssl_context()
    return {
        "http_client": httpx.Client(verify=verify),
        "async_http_client": httpx.AsyncClient(verify=verify),
    }


def build_google_genai_http_options() -> dict[str, Any]:
    """Build HTTP options for the google-genai SDK.

    Returns a dict (not HttpOptions) so SSLContext is not serialized by Pydantic.
    """
    ssl_context = build_ssl_context()
    return {
        "async_client_args": {"ssl": ssl_context},
        "client_args": {"verify": ssl_context},
    }
