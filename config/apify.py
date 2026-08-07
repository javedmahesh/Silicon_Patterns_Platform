"""Apify platform configuration for Decision Maker Intelligence engine.

Handles credential loading, actor ID configuration, and API defaults.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def load_apify_credentials() -> tuple[str, str]:
    """Load Apify API token and actor ID from environment.

    Returns:
        (api_token, actor_id) tuple. Both may be empty if not configured.
    """
    api_token = (
        os.getenv("APIFY_API_TOKEN") or
        os.getenv("APIFY_TOKEN") or
        ""
    ).strip()

    actor_id = (
        os.getenv("APIFY_ACTOR_ID") or
        os.getenv("DECISION_MAKER_ACTOR_ID") or
        "T1XDXWc1L92AfIJtd"  # Default actor ID
    ).strip()

    return api_token, actor_id


# API defaults
# NOTE: the leads-scraper-ppe actor caps `companyDomain` at maxItems=10 per run,
# so the batch size MUST stay <= 10 or Apify rejects the input (HTTP 400).
DEFAULT_BATCH_SIZE = 10  # companies per Apify call (actor hard limit: 10 domains)
DEFAULT_TIMEOUT_SECONDS = 300  # per-HTTP-call timeout (create / poll / dataset fetch)
DEFAULT_RETRIES = 3  # max RUN-CREATION attempts (not poll attempts -- see apify_source.py)
DEFAULT_RETRY_BACKOFF = 1.5  # exponential backoff multiplier (creation retries only)
DEFAULT_TOTAL_RESULTS = 1000  # leads per run (actor allows 100..30000)

# Decision Maker execution lifecycle (poll, don't re-create): once a run exists,
# it is polled -- GET /actor-runs/{id} -- until it reaches a terminal state.
# READY/RUNNING are normal and never trigger a new run. Both knobs are
# configurable via environment variables (sensible defaults below) so a slower or
# faster actor doesn't need a code change.
DEFAULT_POLL_INTERVAL_SECONDS = float(os.getenv("APIFY_POLL_INTERVAL_SECONDS", "5"))
DEFAULT_MAX_WAIT_SECONDS = int(os.getenv("APIFY_MAX_WAIT_SECONDS", "300"))

# Apify API endpoint
APIFY_BASE_URL = "https://api.apify.com/v2"

# Director+ seniority values, in THIS actor's exact enum vocabulary (title-case).
# The actor's allowed set is:
#   Founder, Chairman, President, CEO, CXO, Vice President, Director, Head,
#   Manager, Senior, Junior, Entry Level, Executive
# We keep only director-and-above bands (Manager and ICs are gated out).
APIFY_DIRECTOR_SENIORITY: tuple[str, ...] = (
    "Founder", "Chairman", "President", "CEO", "CXO", "Vice President", "Director", "Head",
)


