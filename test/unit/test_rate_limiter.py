"""Unit tests for the token-bucket rate limiter.

wait_if_rate_limited() previously referenced an undefined `logger` name,
so any call that actually hit the "rate limited" branch raised a
NameError instead of logging a warning. test_wait_if_rate_limited_logs_instead_of_crashing
guards against that regressing. It also never called record_request(),
so the limiter's internal history stayed empty forever and
can_make_request() was permissive no matter how many calls went through;
the tests below assert record_request() is now called once admitted.
"""

from datetime import datetime, timedelta

import pytest

from mcp_kipris.kipris import rate_limiter as rate_limiter_module
from mcp_kipris.kipris.rate_limiter import (
    RateLimiter,
    TokenBucket,
    wait_if_rate_limited,
    wait_if_rate_limited_sync,
)

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


class _FlakyLimiter:
    """Denies the first `denials` calls to can_make_request(), then allows."""

    def __init__(self, denials=1):
        self._remaining_denials = denials
        self.calls = 0
        self.recorded = 0

    def can_make_request(self):
        self.calls += 1
        if self._remaining_denials > 0:
            self._remaining_denials -= 1
            return False
        return True

    def record_request(self):
        self.recorded += 1


@pytest.mark.asyncio
async def test_wait_if_rate_limited_logs_instead_of_crashing(monkeypatch):
    limiter = _FlakyLimiter(denials=1)

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(rate_limiter_module, "get_rate_limiter", lambda: limiter)
    monkeypatch.setattr(rate_limiter_module.asyncio, "sleep", _no_sleep)

    await wait_if_rate_limited()

    assert limiter.calls == 2
    assert limiter.recorded == 1


def test_wait_if_rate_limited_sync_records_once_admitted(monkeypatch):
    limiter = _FlakyLimiter(denials=2)

    monkeypatch.setattr(rate_limiter_module, "get_rate_limiter", lambda: limiter)
    monkeypatch.setattr(rate_limiter_module.time, "sleep", lambda _seconds: None)

    wait_if_rate_limited_sync()

    assert limiter.calls == 3
    assert limiter.recorded == 1


@pytest.mark.asyncio
async def test_wait_if_rate_limited_records_immediately_when_not_limited(monkeypatch):
    limiter = _FlakyLimiter(denials=0)
    monkeypatch.setattr(rate_limiter_module, "get_rate_limiter", lambda: limiter)

    await wait_if_rate_limited()

    assert limiter.calls == 1
    assert limiter.recorded == 1
