import pytest

from mcp_kipris.kipris.errors import (
    KiprisConnectionError,
    KiprisErrorCode,
    KiprisHttpError,
    KiprisParseError,
    KiprisRateLimitError,
    KiprisTimeoutError,
)

pytestmark = pytest.mark.unit


def test_timeout_error_to_dict():
    error = KiprisTimeoutError(timeout_seconds=30)

    assert error.to_dict() == {
        "error": "TIMEOUT",
        "message": "Request timeout after 30 seconds",
        "details": {"timeout_seconds": 30},
    }


def test_connection_error_wraps_original_exception():
    original = ConnectionRefusedError("refused")

    error = KiprisConnectionError(original)

    assert error.code == KiprisErrorCode.CONNECTION_ERROR
    assert "refused" in error.message
    assert error.details["original_error"] == "refused"


def test_http_error_truncates_long_response_text():
    long_body = "x" * 500

    error = KiprisHttpError(status_code=500, response_text=long_body)

    assert error.code == KiprisErrorCode.HTTP_ERROR
    assert len(error.details["response_preview"]) == 200


def test_rate_limit_error_includes_retry_after():
    error = KiprisRateLimitError(retry_after=15)

    assert error.details["retry_after"] == 15
    assert "15 seconds" in error.message


def test_parse_error_includes_parse_failure_reason():
    error = KiprisParseError(parse_error="unexpected EOF", response_text="<broken")

    assert error.code == KiprisErrorCode.PARSE_ERROR
    assert "unexpected EOF" in error.message
    assert error.details["parse_error"] == "unexpected EOF"
