"""Unit tests for ABSKiprisAPI's request plumbing.

Covers three regressions:
1. sync_call/async_call never consulted the rate limiter at all, so the
   configured limit was pure decoration.
2. The request URL — which embeds the real KIPRIS accessKey in its query
   string — was logged verbatim instead of through redact_sensitive_data(),
   the exact utility built to prevent secrets from reaching logs.
3. parse_response() collapsed every non-"00" KIPRIS result code into a
   silent empty DataFrame, so a genuine API error (bad key, unauthorized
   service, expired deadline, ...) was indistinguishable from "nothing
   matched". Confirmed live: trademark_search returned "there is no
   result" for every query because the API key isn't authorized for that
   service (result code 31), not because there were no matches.
"""

import logging

import pytest

from mcp_kipris.kipris.api import abs_class
from mcp_kipris.kipris.errors import KiprisApiError

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


def _response(result_code, result_msg="msg", item=None):
    body = {"item": item} if item is not None else {}
    return {"response": {"header": {"resultCode": result_code, "resultMsg": result_msg}, "body": body}}


def test_parse_response_returns_empty_dataframe_for_no_results_code():
    api = _api()
    api.KEY_STRING = "response.body.item"

    result = api.parse_response(_response("20", "NO_RESULTS"))

    assert result.empty


def test_parse_response_raises_for_a_genuine_api_error():
    api = _api()
    api.KEY_STRING = "response.body.item"

    with pytest.raises(KiprisApiError) as exc_info:
        api.parse_response(_response("31", "DEADLINE_HAS_EXPIRED_ERROR"))

    assert "31" in str(exc_info.value)
    assert "DEADLINE_HAS_EXPIRED_ERROR" in str(exc_info.value)


@pytest.mark.parametrize("result_code", ["10", "30", "99"])
def test_parse_response_raises_for_other_known_and_unknown_error_codes(result_code):
    api = _api()
    api.KEY_STRING = "response.body.item"

    with pytest.raises(KiprisApiError):
        api.parse_response(_response(result_code))


def test_parse_response_raises_for_none_response():
    api = _api()
    api.KEY_STRING = "response.body.item"

    with pytest.raises(KiprisApiError):
        api.parse_response(None)


def test_parse_response_returns_data_for_a_successful_response():
    api = _api()
    api.KEY_STRING = "response.body.item"

    result = api.parse_response(_response("00", "NORMAL_SERVICE", item={"applicationNumber": "123"}))

    assert not result.empty
    assert result.iloc[0]["applicationNumber"] == "123"


# --- totalCount: needed for any aggregation across paginated results -------


def _response_with_count(item, total_count):
    # count is a sibling of header/body (response.count.totalCount), not
    # nested under body -- confirmed against the live KIPRIS API.
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
            "body": {"item": item},
            "count": {"totalCount": str(total_count)},
        }
    }


def test_parse_response_attaches_total_count_from_kipris_count_block():
    api = _api()
    api.KEY_STRING = "response.body.item"

    result = api.parse_response(_response_with_count({"applicationNumber": "123"}, total_count=42))

    assert result.attrs["total_count"] == 42


def test_parse_response_total_count_defaults_to_row_count_when_kipris_omits_it():
    api = _api()
    api.KEY_STRING = "response.body.item"

    result = api.parse_response(_response("00", "NORMAL_SERVICE", item={"applicationNumber": "123"}))

    assert result.attrs["total_count"] == 1


def test_parse_response_total_count_is_zero_for_no_results_code():
    api = _api()
    api.KEY_STRING = "response.body.item"

    result = api.parse_response(_response("20", "NO_RESULTS"))

    assert result.attrs["total_count"] == 0
