"""
Rate limiting utilities for KIPRIS API requests.
Implements token bucket algorithm to prevent API throttling.
"""

import asyncio
import logging
import threading
import time
from typing import Optional
from collections import deque
from datetime import datetime, timedelta

logger = logging.getLogger("mcp-kipris")


class TokenBucket:
    """Token bucket for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float, tokens_per_refill: int = 1):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens the bucket can hold
            refill_rate: Rate at which tokens are added (tokens per second)
            tokens_per_refill: Number of tokens added each refill
        """
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.tokens_per_refill = tokens_per_refill
        self.last_refill = datetime.now()
        self._lock = threading.Lock()

    def consume(self, tokens: int) -> bool:
        """
        Try to consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False otherwise
        """
        with self._lock:
            now = datetime.now()
            # Refill tokens based on time elapsed
            time_elapsed = (now - self.last_refill).total_seconds()
            tokens_to_add = int(time_elapsed * self.refill_rate)

            if tokens_to_add > 0:
                self.tokens = min(self.capacity, self.tokens + tokens_to_add)
                self.last_refill = now
            else:
                self.tokens = max(0, self.tokens + tokens_to_add)

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False


class RateLimiter:
    """Rate limiter for KIPRIS API requests."""

    def __init__(self, max_requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests_per_minute: Maximum requests allowed per minute
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.requests = deque(maxlen=max_requests_per_minute)
        self._lock = threading.Lock()

    def can_make_request(self) -> bool:
        """
        Check if a request can be made.

        Returns:
            True if request is allowed, False otherwise
        """
        with self._lock:
            now = datetime.now()
            # Remove requests older than 1 minute
            one_minute_ago = now - timedelta(minutes=1)

            # Filter old requests
            while self.requests and self.requests[0] < one_minute_ago:
                self.requests.popleft()

            # Check if we can make a new request
            if len(self.requests) < self.max_requests_per_minute:
                return True
            else:
                return False

    def record_request(self) -> None:
        """Record a successful request."""
        with self._lock:
            self.requests.append(datetime.now())


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(max_requests_per_minute: int = 60) -> RateLimiter:
    """
    Get or create a rate limiter instance.

    Args:
        max_requests_per_minute: Maximum requests per minute

    Returns:
        RateLimiter instance
    """
    global _rate_limiter

    if _rate_limiter is None:
        _rate_limiter = RateLimiter(max_requests_per_minute)

    return _rate_limiter


_POLL_INTERVAL_SECONDS = 1.0


async def wait_if_rate_limited() -> None:
    """
    Wait if rate limited, then record the request. Must be called
    immediately before making an API request (see ABSKiprisAPI.async_call).
    """
    rate_limiter = get_rate_limiter()

    while not rate_limiter.can_make_request():
        logger.warning(f"Rate limit reached. Waiting {_POLL_INTERVAL_SECONDS:.1f} seconds before retrying.")
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)

    rate_limiter.record_request()


def wait_if_rate_limited_sync() -> None:
    """
    Synchronous counterpart to wait_if_rate_limited(), for use in
    ABSKiprisAPI.sync_call.
    """
    rate_limiter = get_rate_limiter()

    while not rate_limiter.can_make_request():
        logger.warning(f"Rate limit reached. Waiting {_POLL_INTERVAL_SECONDS:.1f} seconds before retrying.")
        time.sleep(_POLL_INTERVAL_SECONDS)

    rate_limiter.record_request()
