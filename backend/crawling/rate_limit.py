"""Rate limiting and concurrency control.

Two independent limits, because they bound different things:

* **Rate** — requests per minute, enforced by a token bucket. Protects the provider's
  quota and the target site from a burst.
* **Concurrency** — simultaneous in-flight requests, enforced by a semaphore. Protects
  the crawler itself from opening more sockets than it can service.

Both are per-host as well as global, so one slow site cannot consume the whole
budget and one aggressive crawl cannot hammer a single origin. Politeness toward the
sites being crawled is a hard requirement of this layer, not a nicety.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlparse

logger = logging.getLogger("crawling.rate_limit")


def host_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


class TokenBucket:
    """Classic token bucket: ``rate_per_minute`` tokens refilled continuously.

    Chosen over a fixed window because a window lets 2x the limit land across a
    boundary — exactly the burst that gets a crawler blocked.
    """

    def __init__(self, rate_per_minute: int, *, burst: int | None = None) -> None:
        self.rate_per_minute = max(0, rate_per_minute)
        self._capacity = float(burst if burst is not None else max(1, self.rate_per_minute))
        self._tokens = self._capacity
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    @property
    def unlimited(self) -> bool:
        return self.rate_per_minute <= 0

    def _refill(self, now: float) -> None:
        elapsed = now - self._updated
        if elapsed <= 0:
            return
        self._tokens = min(self._capacity, self._tokens + elapsed * (self.rate_per_minute / 60.0))
        self._updated = now

    def try_acquire(self) -> bool:
        if self.unlimited:
            return True
        with self._lock:
            self._refill(time.monotonic())
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def time_until_token(self) -> float:
        """Seconds until one token is available (0 when one is ready now)."""
        if self.unlimited:
            return 0.0
        with self._lock:
            self._refill(time.monotonic())
            if self._tokens >= 1.0:
                return 0.0
            deficit = 1.0 - self._tokens
            return deficit / (self.rate_per_minute / 60.0)

    def acquire(self, *, timeout: float | None = None) -> bool:
        """Block until a token is free. ``False`` if ``timeout`` elapsed first."""
        if self.unlimited:
            return True
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            if self.try_acquire():
                return True
            wait = self.time_until_token()
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                wait = min(wait, remaining)
            time.sleep(max(0.01, min(wait, 1.0)))


@dataclass(slots=True)
class RateLimitConfig:
    requests_per_minute: int = 60
    per_host_requests_per_minute: int = 30
    max_concurrency: int = 4
    max_per_host_concurrency: int = 2
    acquire_timeout_seconds: float = 60.0


class RateLimiter:
    """Global + per-host rate and concurrency gate.

    Used as a context manager around one request:

        with limiter.slot(url):
            ...perform the request...

    Acquisition order is global-then-host and release is the reverse, which is what
    prevents two threads deadlocking on opposite orders.
    """

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        self._global_bucket = TokenBucket(self.config.requests_per_minute)
        self._global_sem = threading.BoundedSemaphore(max(1, self.config.max_concurrency))
        self._host_buckets: dict[str, TokenBucket] = {}
        self._host_sems: dict[str, threading.BoundedSemaphore] = {}
        self._lock = threading.Lock()
        self.throttled = 0          # times a caller had to wait for a token

    def _for_host(self, host: str) -> tuple[TokenBucket, threading.BoundedSemaphore]:
        with self._lock:
            bucket = self._host_buckets.get(host)
            if bucket is None:
                bucket = TokenBucket(self.config.per_host_requests_per_minute)
                self._host_buckets[host] = bucket
                self._host_sems[host] = threading.BoundedSemaphore(
                    max(1, self.config.max_per_host_concurrency))
            return bucket, self._host_sems[host]

    def slot(self, url: str) -> "_Slot":
        return _Slot(self, host_of(url), url)

    # ---------------------------------------------------------------- internals
    def _acquire(self, host: str, url: str) -> None:
        timeout = self.config.acquire_timeout_seconds
        if not self._global_sem.acquire(timeout=timeout):
            raise TimeoutError(f"crawl concurrency slot not available within {timeout}s")
        host_bucket, host_sem = self._for_host(host)
        try:
            if not host_sem.acquire(timeout=timeout):
                raise TimeoutError(f"per-host concurrency slot for {host} not available")
        except BaseException:
            self._global_sem.release()
            raise

        try:
            for bucket, label in ((self._global_bucket, "global"), (host_bucket, host)):
                if bucket.time_until_token() > 0:
                    self.throttled += 1
                    logger.debug("[crawl] throttled by %s limiter before %s", label, url)
                if not bucket.acquire(timeout=timeout):
                    raise TimeoutError(f"rate limit ({label}) not satisfied within {timeout}s")
        except BaseException:
            host_sem.release()
            self._global_sem.release()
            raise

    def _release(self, host: str) -> None:
        _bucket, host_sem = self._for_host(host)
        try:
            host_sem.release()
        finally:
            self._global_sem.release()

    def stats(self) -> dict[str, int]:
        with self._lock:
            hosts = len(self._host_buckets)
        return {"throttled": self.throttled, "tracked_hosts": hosts,
                "requests_per_minute": self.config.requests_per_minute,
                "max_concurrency": self.config.max_concurrency}


class _Slot:
    """One acquired request slot. Released on exit, including on exception."""

    __slots__ = ("_limiter", "_host", "_url", "_held")

    def __init__(self, limiter: RateLimiter, host: str, url: str) -> None:
        self._limiter = limiter
        self._host = host
        self._url = url
        self._held = False

    def __enter__(self) -> "_Slot":
        self._limiter._acquire(self._host, self._url)
        self._held = True
        return self

    def __exit__(self, *exc) -> None:
        if self._held:
            self._held = False
            self._limiter._release(self._host)
