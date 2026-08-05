"""Retry policy for crawl requests.

Retries only what a retry can fix. A 404, a 401, or a malformed URL will fail
identically on the second attempt, so retrying them wastes the rate-limit budget and
delays the caller — those are :class:`PermanentCrawlError` and fail fast.

Backoff is exponential with full jitter. Jitter matters here specifically: several
crawlers retrying a recovering provider in lockstep is what turns a blip into an
outage. A provider-supplied ``Retry-After`` always wins over the computed delay,
because the provider knows better than we do.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

from backend.crawling.schemas import CrawlError, PermanentCrawlError, RateLimited

logger = logging.getLogger("crawling.retry")

T = TypeVar("T")

#: HTTP statuses worth another attempt: transient server/proxy faults and throttling.
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504, 522, 524})


@dataclass(slots=True)
class RetryPolicy:
    attempts: int = 3                    # total attempts, not retries (1 = no retry)
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    multiplier: float = 2.0
    jitter: bool = True
    respect_retry_after: bool = True

    def delay_for(self, attempt: int, *, retry_after: float = 0.0) -> float:
        """Seconds to wait before ``attempt`` (1-based) is retried."""
        if self.respect_retry_after and retry_after > 0:
            return min(retry_after, self.max_delay_seconds)
        raw = self.base_delay_seconds * (self.multiplier ** max(0, attempt - 1))
        capped = min(raw, self.max_delay_seconds)
        # Full jitter: uniform in [0, capped]. Spreads a thundering herd far better
        # than the equal-jitter variants at the cost of a slightly longer mean wait.
        return random.uniform(0, capped) if self.jitter else capped

    @classmethod
    def from_settings(cls, settings) -> "RetryPolicy":
        return cls(
            attempts=getattr(settings, "crawl_retry_count", cls.attempts),
            base_delay_seconds=getattr(settings, "crawl_retry_backoff_seconds",
                                       cls.base_delay_seconds),
            max_delay_seconds=getattr(settings, "crawl_retry_max_backoff_seconds",
                                      cls.max_delay_seconds),
        )


def is_retryable(exc: BaseException) -> bool:
    """Whether another attempt could plausibly succeed."""
    if isinstance(exc, PermanentCrawlError):
        return False
    if isinstance(exc, CrawlError):
        return exc.retryable
    # Transport-level faults from any HTTP library: no response was produced, so the
    # request may simply not have landed.
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


def status_is_retryable(status_code: int) -> bool:
    return status_code in RETRYABLE_STATUS


@dataclass(slots=True)
class RetryOutcome:
    attempts: int = 0
    total_delay_seconds: float = 0.0
    last_error: str = ""


def with_retries(
    fn: Callable[[], T],
    policy: RetryPolicy | None = None,
    *,
    label: str = "",
    sleep: Callable[[float], None] = time.sleep,
    outcome: RetryOutcome | None = None,
) -> T:
    """Run ``fn`` under ``policy``, re-raising the final error.

    ``sleep`` is injectable so tests exercise the backoff arithmetic without
    actually waiting. ``outcome``, when supplied, is filled in with what happened —
    the caller records attempts on the crawl result without the policy needing to
    know about crawl results.
    """
    p = policy or RetryPolicy()
    record = outcome if outcome is not None else RetryOutcome()
    total = max(1, p.attempts)

    for attempt in range(1, total + 1):
        record.attempts = attempt
        try:
            return fn()
        except BaseException as exc:      # noqa: BLE001 - re-raised below
            record.last_error = str(exc)[:500]
            if not is_retryable(exc) or attempt >= total:
                if attempt >= total and is_retryable(exc):
                    logger.warning("[crawl] %s: giving up after %d attempt(s): %s",
                                   label or "request", attempt, record.last_error)
                raise
            retry_after = getattr(exc, "retry_after", 0.0) if isinstance(exc, RateLimited) else 0.0
            delay = p.delay_for(attempt, retry_after=retry_after)
            record.total_delay_seconds += delay
            logger.info("[crawl] %s: attempt %d/%d failed (%s) — retrying in %.2fs",
                        label or "request", attempt, total, record.last_error, delay)
            sleep(delay)

    raise RuntimeError("unreachable: retry loop exhausted without returning")   # pragma: no cover
