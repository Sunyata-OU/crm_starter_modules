"""Fixtures for the module tests.

Only ``db_redis`` has tests today, and they run against a **real Redis** rather
than a fake. That is deliberate: what the provider relies on is `WATCH`/`MULTI`
aborting a transaction when the key moved, and a fake that gets that subtly
wrong would pass the suite while the thing it is meant to prove -- that two
workers cannot claim the same job -- quietly failed in production.

Without a server, the suite skips. It does not silently pass.
"""

from __future__ import annotations

import os

import pytest

REDIS_URL = os.environ.get("CRM_TEST_REDIS_URL", "redis://localhost:6379/15")


@pytest.fixture(scope="session")
def redis_url() -> str:
    pytest.importorskip("redis", reason="the redis package is not installed")
    import asyncio

    from redis.asyncio import Redis

    async def ping() -> bool:
        client = Redis.from_url(REDIS_URL, socket_connect_timeout=1)
        try:
            await client.ping()
            return True
        except Exception:
            return False
        finally:
            await client.aclose()

    if not asyncio.run(ping()):
        pytest.skip(f"no Redis at {REDIS_URL}; set CRM_TEST_REDIS_URL to point at one")
    return REDIS_URL
