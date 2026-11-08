"""Tests for shared HTTP/SSL helpers."""

from __future__ import annotations

from app.utils.google_http import SSLContextHTTPAdapter, build_requests_session


def test_build_requests_session_mounts_ssl_adapter() -> None:
    session = build_requests_session()
    adapter = session.get_adapter("https://example.com")
    assert isinstance(adapter, SSLContextHTTPAdapter)


def test_ssl_context_adapter_uses_shared_ssl_context() -> None:
    ssl_context = object()
    adapter = SSLContextHTTPAdapter(ssl_context)
    assert adapter._ssl_context is ssl_context
