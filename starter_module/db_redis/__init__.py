"""Redis as a backing store, and as somewhere to put the job queue.

Adds a ``redis`` connection type and the provider behind it, so a resource can
name ``redis.jobs#jobs`` the way another names ``db.main#deals``. Nothing else
changes: the same screens, the same query language, the same contract.

```yaml
# connections.yaml
connections:
  redis.jobs:
    type: redis
    url: ${CRM_REDIS_JOBS_URL:-redis://localhost:6379/1}
    prefix: crm:jobs
    # Fields worth an index. Equality on the first, ranges on the second --
    # between them they are the queue's claim query.
    indexed: [status, kind, claimed_by, key]
    scored: [run_at, priority, created_at, finished_at]
```

```bash
uv pip install 'crm-starter-modules[redis]'
CRM_MODULES=db_redis CRM_JOBS_CONNECTION=redis.jobs uv run crm worker
```

**What this is good for, and what it is not.** The job queue's one hard
requirement of its store is a conditional write, and Redis has a real one:
``WATCH``/``MULTI`` aborts the transaction if the key moved, which is exactly
the compare-and-set that stops two workers claiming the same job. So the queue
works here, and on a busy one it works well -- the claim query becomes one set
intersection and one sorted-set range rather than a table scan.

What it does not give you is better durability. Redis persistence is `RDB`
snapshots or `AOF`, and the default fsync policy can lose about a second of
writes on a hard stop. For a cache that is the right trade. For a queue whose
whole purpose is that accepted work is not lost, it is the property you were
paying to avoid -- so run this with `appendonly yes` and `appendfsync always`
if the jobs matter, and know that this is still weaker than the database you
already run. `CRM_JOBS_CONNECTION=db.main` remains the safe default, and this
module is the answer to *throughput*, not to durability.

The provider is general: point any resource at it, not only the queue. It is
just that a queue is the case where the indexes earn their keep.
"""

from __future__ import annotations

from typing import Any

from app.core.connections import ConnectionSpec, register_connection
from app.core.errors import ConfigError
from app.core.registry import Registry, register_provider_factory

from .provider import DEFAULT_MAX_ROWS, RedisProvider

MANIFEST = {
    "name": "db_redis",
    "label": "Redis Provider",
    "description": "A redis connection type and provider, for the job queue or any resource.",
    "depends": (),
    # Needs a Redis server and the `redis` package, so it is never implicit.
    "optional": True,
}

__all__ = ["MANIFEST", "RedisConnection", "RedisProvider", "register"]


class RedisConnection:
    """An open client, plus the defaults every provider on it inherits.

    The index declarations live on the connection rather than on each resource
    because they describe the keyspace, and two resources sharing a prefix that
    disagreed about its indexes would corrupt each other's.
    """

    def __init__(
        self,
        client: Any,
        *,
        prefix: str = "crm",
        indexed: tuple[str, ...] = (),
        scored: tuple[str, ...] = (),
        max_rows: int = DEFAULT_MAX_ROWS,
    ) -> None:
        self.client = client
        self.prefix = prefix.rstrip(":")
        self.indexed = indexed
        self.scored = scored
        self.max_rows = max_rows

    async def close(self) -> None:
        await self.client.aclose()

    async def check(self) -> tuple[bool, str]:
        pong = await self.client.ping()
        return bool(pong), f"connected to {self.prefix!r}"


def _names(spec: ConnectionSpec, key: str) -> tuple[str, ...]:
    """A list option, tolerating the comma-separated string YAML may produce."""
    raw = spec.option(key, ())
    if isinstance(raw, str):
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    return tuple(str(item) for item in raw or ())


@register_connection(
    "redis",
    close=lambda conn: conn.close(),
    check=lambda conn: conn.check(),
)
async def open_redis(spec: ConnectionSpec) -> RedisConnection:
    try:
        from redis.asyncio import Redis
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on the install
        raise ConfigError(
            f"connection {spec.name!r} is a redis connection, but the 'redis' package "
            f"is not installed. Install it with: uv pip install 'crm-starter-modules[redis]'"
        ) from exc

    client = Redis.from_url(
        spec.option("url", required=True),
        # Values come back as text rather than bytes, so a record is JSON the
        # moment it is read and index members compare as the strings they are.
        decode_responses=True,
        socket_timeout=spec.number("timeout", 5),
        socket_connect_timeout=spec.number("connect_timeout", 5),
        health_check_interval=spec.number("health_check_interval", 30),
    )
    return RedisConnection(
        client,
        prefix=str(spec.option("prefix", "crm")),
        indexed=_names(spec, "indexed"),
        scored=_names(spec, "scored"),
        max_rows=spec.number("max_rows", DEFAULT_MAX_ROWS),
    )


@register_provider_factory("redis")
def build_redis_provider(handle: RedisConnection, target: str, resource: Any) -> RedisProvider:
    """Wire a resource declaring ``redis.name#collection`` to that keyspace."""
    collection = target or resource.name
    return RedisProvider(
        handle.client,
        f"{handle.prefix}:{collection}" if handle.prefix else collection,
        name=f"redis:{collection}",
        pk_field=resource.pk,
        searchable_fields=resource.searchable_fields(),
        indexed=handle.indexed,
        scored=handle.scored,
        max_rows=handle.max_rows,
    )


def register(registry: Registry) -> None:
    """Nothing to declare.

    Importing this module is what registers the connection type and the
    provider factory, which happens before anything binds -- so a resource
    naming a ``redis`` connection resolves. The module exists to make that
    import a thing a deployment switches on, rather than a line somebody has to
    remember to add.
    """
    return
