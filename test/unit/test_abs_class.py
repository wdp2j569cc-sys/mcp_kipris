"""Unit tests for ABSKiprisAPI's request plumbing.

Covers two regressions fixed alongside the rate limiter wiring:
1. sync_call/async_call never consulted the rate limiter at all, so the
   configured limit was pure decoration.
2. The request URL — which embeds the real KIPRIS accessKey in its query
   string — was logged verbatim instead of through redact_sensitive_data(),
   the exact utility built to prevent secrets from reaching logs.
"""

import logging

import pytest

from mcp_kipris.kipris.api import abs_class

pytestmark = pytest.mark.unit


def _api():
    return abs_class.ABSKiprisAPI(api_key="SECRET_TEST_KEY")


def test_sync_call_waits_for_rate_limiter_before_requesting(monkeypatch):
    calls = []
    monkeypatch.setattr(abs_class, "wait_if_rate_limited_sync", lambda: calls.append("rate_limit"))
    monkeypatch.setattr(abs_class, "get_response", lambda url: calls.append("request") or {})

    _api().sync_call(api_url="http://example.com/api")

    assert calls == ["rate_limit", "request"]


@pytest.mark.asyncio
async def test_async_call_waits_for_rate_limiter_before_requesting(monkeypatch):
    calls = []

    async def _fake_wait():
        calls.append("rate_limit")

    async def _fake_get_response_async(url):
        calls.append("request")
        return {}

    monkeypatch.setattr(abs_class, "wait_if_rate_limited", _fake_wait)
    monkeypatch.setattr(abs_class, "get_response_async", _fake_get_response_async)

    await _api().async_call(api_url="http://example.com/api")

    assert calls == ["rate_limit", "request"]


def test_sync_call_does_not_log_the_raw_api_key(monkeypatch, caplog):
    monkeypatch.setattr(abs_class, "wait_if_rate_limited_sync", lambda: None)
    monkeypatch.setattr(abs_class, "get_response", lambda url: {})

    with caplog.at_level(logging.INFO, logger="mcp-kipris"):
        _api().sync_call(api_url="http://example.com/api")

    assert "SECRET_TEST_KEY" not in caplog.text
    assert "REDACTED" in caplog.text


@pytest.mark.asyncio
async def test_async_call_does_not_log_the_raw_api_key(monkeypatch, caplog):
    async def _fake_wait():
        return None

    async def _fake_get_response_async(url):
        return {}

    monkeypatch.setattr(abs_class, "wait_if_rate_limited", _fake_wait)
    monkeypatch.setattr(abs_class, "get_response_async", _fake_get_response_async)

    with caplog.at_level(logging.INFO, logger="mcp-kipris"):
        await _api().async_call(api_url="http://example.com/api")

    assert "SECRET_TEST_KEY" not in caplog.text
    assert "REDACTED" in caplog.text
