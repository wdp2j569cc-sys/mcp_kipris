"""get_response()/get_response_async() log the request URL — which embeds
the real KIPRIS accessKey — at several points (start, result header,
error paths). These tests pin down that every one of those log lines goes
through redact_sensitive_data() instead of leaking the raw query string.
"""

import logging

import pytest

from mcp_kipris.kipris.api import utils as api_utils

pytestmark = pytest.mark.unit

SECRET_URL = "http://plus.kipris.or.kr/openapi/rest/service?accessKey=SECRET_TEST_KEY&query=x"

SAMPLE_XML = "<response><header><resultCode>00</resultCode></header><body><items/></body></response>"


class _FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


def test_get_response_does_not_log_the_raw_api_key(monkeypatch, caplog):
    class _FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def get(self, url, timeout):
            return _FakeResponse(SAMPLE_XML)

    monkeypatch.setattr(api_utils.requests, "Session", _FakeSession)

    with caplog.at_level(logging.INFO, logger="mcp-kipris"):
        api_utils.get_response(SECRET_URL)

    assert "SECRET_TEST_KEY" not in caplog.text
    assert "REDACTED" in caplog.text


@pytest.mark.asyncio
async def test_get_response_async_does_not_log_the_raw_api_key(monkeypatch, caplog):
    class _FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def get(self, url):
            return _FakeResponse(SAMPLE_XML)

    monkeypatch.setattr(api_utils.httpx, "AsyncClient", lambda *a, **kw: _FakeAsyncClient())

    with caplog.at_level(logging.INFO, logger="mcp-kipris"):
        await api_utils.get_response_async(SECRET_URL)

    assert "SECRET_TEST_KEY" not in caplog.text
    assert "REDACTED" in caplog.text
