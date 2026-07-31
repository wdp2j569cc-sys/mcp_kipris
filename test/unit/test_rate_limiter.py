"""Unit tests for the token-bucket rate limiter.

wait_if_rate_limited() previously referenced an undefined `logger` name,
so any call that actually hit the "rate limited" branch raised a
NameError instead of logging a warning. test_wait_if_rate_limited_logs_instead_of_crashing
guards against that regressing.
"""

from datetime import datetime, timedelta

import pytest

from mcp_kipris.kipris import rate_limiter as rate_limiter_module
from mcp_kipris.kipris.rate_limiter import RateLimiter, TokenBucket, wait_if_rate_limited

pytestmark = pytest.mark.unit


def test_token_bucket_consumes_available_tokens():
    bucket = TokenBucket(capacity=5, refill_rate=1)

    assert bucket.consume(3) is True
    assert bucket.tokens == 2


def test_token_bucket_refuses_when_insufficient_tokens():
    bucket = TokenBucket(capacity=5, refill_rate=1)

    assert bucket.consume(10) is False
    assert bucket.tokens == 5


def test_token_bucket_time_until_available_is_zero_when_enough_tokens():
    bucket = TokenBucket(capacity=5, refill_rate=1)

    assert bucket.time_until_available(3) == 0.0


def test_token_bucket_time_until_available_is_positive_when_depleted():
    bucket = TokenBucket(capacity=5, refill_rate=2)
    bucket.consume(5)

    wait_seconds = bucket.time_until_available(4)

    assert wait_seconds == pytest.approx(2.0)


def test_rate_limiter_allows_requests_under_the_limit():
    limiter = RateLimiter(max_requests_per_minute=2)

    assert limiter.can_make_request() is True
    limiter.record_request()
    assert limiter.can_make_request() is True
    limiter.record_request()
    assert limiter.can_make_request() is False


def test_rate_limiter_expires_requests_older_than_one_minute():
    limiter = RateLimiter(max_requests_per_minute=1)
    limiter.requests.append(datetime.now() - timedelta(minutes=2))

    assert limiter.can_make_request() is True


@pytest.mark.asyncio
async def test_wait_if_rate_limited_logs_instead_of_crashing(monkeypatch):
    call_count = {"n": 0}

    class _FlakyLimiter:
        def can_make_request(self):
            call_count["n"] += 1
            return call_count["n"] > 1

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(rate_limiter_module, "get_rate_limiter", lambda: _FlakyLimiter())
    monkeypatch.setattr(rate_limiter_module.asyncio, "sleep", _no_sleep)

    await wait_if_rate_limited()

    assert call_count["n"] == 2
