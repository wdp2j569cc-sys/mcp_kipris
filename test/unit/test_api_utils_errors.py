"""Regression tests for get_response()/get_response_async() error handling.

Previously every exception path here (timeout, connection error, HTTP
error, non-XML response, and anything else unexpected) was caught and
converted into an empty {} return. abs_class.py's parse_response() then
read that {} exactly like a genuine "0 matches" KIPRIS response --
resultCode was missing (not present, not "00"), so check_api_error()
found nothing wrong, and the caller got back an empty DataFrame
indistinguishable from a real empty search. A KIPRIS timeout and "this
search genuinely has no results" looked identical to the end user.

These tests confirm each failure mode now raises the matching
KiprisApiError subclass (already defined and tested in test_errors.py,
but never actually raised in production code before this fix) instead of
being swallowed.
"""

import httpx
import pytest
import requests

from mcp_kipris.kipris.api import utils as api_utils
from mcp_kipris.kipris.errors import (
    KiprisConnectionError,
    KiprisHttpError,
    KiprisParseError,
    KiprisTimeoutError,
)

pytestmark = pytest.mark.unit

URL = "http://plus.kipris.or.kr/openapi/rest/service?accessKey=SECRET&query=x"


class _FakeSession:
    def __init__(self, get_fn):
        self._get_fn = get_fn

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def get(self, url, timeout):
        return self._get_fn(url)


def test_get_response_raises_kipris_timeout_error_not_empty_dict(monkeypatch):
    def _raise_timeout(url):
        raise requests.exceptions.Timeout("connect timed out")

    monkeypatch.setattr(api_utils.requests, "Session", lambda: _FakeSession(_raise_timeout))

    with pytest.raises(KiprisTimeoutError):
        api_utils.get_response(URL)


def test_get_response_raises_kipris_connection_error(monkeypatch):
    def _raise_connection_error(url):
        raise requests.exceptions.ConnectionError("connection reset")

    monkeypatch.setattr(api_utils.requests, "Session", lambda: _FakeSession(_raise_connection_error))

    with pytest.raises(KiprisConnectionError):
        api_utils.get_response(URL)


def test_get_response_raises_kipris_http_error_with_status_and_body():
    class _FakeResponse:
        status_code = 503
        text = "Service Unavailable"

        def raise_for_status(self):
            raise requests.exceptions.HTTPError(response=self)

    def _get(url, timeout):
        return _FakeResponse()

    class _Session:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        get = staticmethod(_get)

    import mcp_kipris.kipris.api.utils as api_utils_mod

    original = api_utils_mod.requests.Session
    api_utils_mod.requests.Session = lambda: _Session()
    try:
        with pytest.raises(KiprisHttpError) as exc_info:
            api_utils.get_response(URL)
        assert exc_info.value.details["status_code"] == 503
    finally:
        api_utils_mod.requests.Session = original


def test_get_response_raises_kipris_parse_error_on_non_xml(monkeypatch):
    class _FakeResponse:
        text = "not xml at all {{{"

        def raise_for_status(self):
            return None

    monkeypatch.setattr(api_utils.requests, "Session", lambda: _FakeSession(lambda url: _FakeResponse()))

    with pytest.raises(KiprisParseError):
        api_utils.get_response(URL)


def test_get_response_reraises_unexpected_exceptions_instead_of_swallowing(monkeypatch):
    def _raise_weird(url):
        raise RuntimeError("something nobody anticipated")

    monkeypatch.setattr(api_utils.requests, "Session", lambda: _FakeSession(_raise_weird))

    with pytest.raises(RuntimeError):
        api_utils.get_response(URL)


@pytest.mark.asyncio
async def test_get_response_async_raises_kipris_timeout_error(monkeypatch):
    class _FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def get(self, url):
            raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(api_utils.httpx, "AsyncClient", lambda *a, **kw: _FakeAsyncClient())

    with pytest.raises(KiprisTimeoutError):
        await api_utils.get_response_async(URL)


@pytest.mark.asyncio
async def test_get_response_async_raises_kipris_http_error():
    class _FakeHttpxResponse:
        status_code = 500
        text = "Internal Server Error"

        def raise_for_status(self):
            raise httpx.HTTPStatusError("500", request=None, response=self)

    class _FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def get(self, url):
            return _FakeHttpxResponse()

    import mcp_kipris.kipris.api.utils as api_utils_mod

    original = api_utils_mod.httpx.AsyncClient
    api_utils_mod.httpx.AsyncClient = lambda *a, **kw: _FakeAsyncClient()
    try:
        with pytest.raises(KiprisHttpError) as exc_info:
            await api_utils.get_response_async(URL)
        assert exc_info.value.details["status_code"] == 500
    finally:
        api_utils_mod.httpx.AsyncClient = original
