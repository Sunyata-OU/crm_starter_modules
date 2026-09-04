# Redis Provider Guide

The `db_redis` module adds a `redis` connection type and the provider behind
it, so a resource can name `redis.jobs#jobs` the way another names
`db.main#deals`. Nothing above the provider changes: the same screens, the same
query language, the same contract.

It exists mainly for one job — putting the **background job queue** on Redis —
but the provider is general and any resource can use it.

## Install

```bash
uv pip install 'crm-starter-modules[redis]'
```

The `redis` package is an optional extra, so the other twelve modules stay
dependency-free.

## Connect

```yaml
# connections.yaml
connections:
  redis.jobs:
    type: redis
    url: ${CRM_REDIS_JOBS_URL:-redis://localhost:6379/1}
    prefix: crm:jobs
    # Fields worth an index. Equality on the first list, ranges on the second.
    indexed: [status, kind, key, claimed_by]
    scored: [run_at, priority, created_at, finished_at]
    max_rows: 5000
```

```bash
CRM_MODULES=db_redis CRM_JOBS_CONNECTION=redis.jobs uv run crm worker
```

`crm check-connections` will confirm it, and `crm capabilities` will show the
`jobs` resource backed by `redis:jobs`.

| Option | Default | What it does |
| --- | --- | --- |
| `url` | *required* | Anything `redis.asyncio.Redis.from_url` accepts. |
| `prefix` | `crm` | Key namespace. A resource's collection name is appended. |
| `indexed` | none | Fields given a set index, for `=` and `in`. |
| `scored` | none | Fields given a sorted-set index, for `<`, `<=`, `>`, `>=` and `between`. |
| `max_rows` | `5000` | Records held in memory to answer one query. |
| `timeout` / `connect_timeout` | `5` | Socket timeouts, in seconds. |

## How queries are answered

Redis has no query engine, so a provider over it must decide where the query
language is answered. This one answers it **exactly, in Python, over a
candidate set that Redis narrows first**.

That split is the design, and both alternatives are worse. Pushing filters into
Redis for the cases it can serve and ignoring the rest returns wrong rows.
Refusing to filter at all and letting the capability shim pull the whole
collection turns a queue with a backlog into an out-of-memory error.

So a read walks the top level of the filter, asks each index what it can,
intersects the answers, fetches only those records — and then runs the real
filter over them with the same `app.providers.local` engine every other
emulated backend uses.

**Narrowing is an optimisation, never a correctness question.** An index that
does not exist costs a wider read, not a wrong answer. An `OR`, a `NOT`, a
filter on an unindexed field: all correct, all slower.

For the queue this is the whole point. `status = 'queued' AND run_at <= now`
becomes one `SMEMBERS` intersected with one `ZRANGEBYSCORE`, so a worker
polling a queue with fifty thousand finished jobs in it reads the handful
actually due.

!!! note "What `crm capabilities` says"
    It will show every stage as `native`, which means "this provider answers it
    exactly, so the shim steps aside" — not "Redis did it". The provider's
    `native_detail()` says so in as many words.

### The row budget

A query that narrows to nothing and finds more than `max_rows` records is
**refused**, not truncated — the same bargain the capability shim makes. If you
hit it, index the field you are filtering on.

## The keyspace

```
<prefix>:<collection>:<id>            a JSON object, one record
<prefix>:<collection>:__seq           the counter behind generated ids
<prefix>:<collection>:__ids           every id, for the unfiltered scan
<prefix>:<collection>:idx:<f>:<v>     ids whose field <f> equals <v>
<prefix>:<collection>:z:<f>           ids scored by field <f>
```

JSON has no datetime, and a queue whose `run_at` came back as a string would
compare as a string — plausibly, and wrongly. So datetimes, dates and decimals
are tagged on the way out and restored on the way in.

## Conditional writes

`update_if` is a real compare-and-set, built on `WATCH`/`MULTI`. Redis aborts
the transaction if the key moved after it was read, and an aborted `EXEC`
becomes the `None` the contract asks for: the loser is told it lost, rather than
getting an error or silently overwriting.

Everything the job queue does rests on this — it is the only thing standing
between two workers and the same job — so it is tested under real contention
against a real server. `tests/test_db_redis.py` races twenty coroutines at one
record and asserts exactly one wins.

## Durability: read this before moving the queue

Redis persistence is `RDB` snapshots or `AOF`, and the default fsync policy can
lose about a second of writes on a hard stop. For a cache that is the right
trade-off. For a queue whose whole purpose is that accepted work is not lost,
it is the property you were paying to avoid.

```conf
appendonly yes
appendfsync always
```

Even then it is weaker than the database you already run. **Redis is the answer
to throughput, not to durability.** `CRM_JOBS_CONNECTION=db.main` remains the
safe default; move the queue when polling a table has actually become the
bottleneck, not before.

## One thing to know about migrations

Moving a resource off SQL makes its old table dead weight, and the next
`crm migrate --autogenerate` will propose dropping it. That is correct — the
schema genuinely no longer includes that table — but it is a destructive
operation in a migration you did not ask for. Read what autogenerate produces,
as always. Nothing is dropped until you run such a migration; switching
`CRM_JOBS_CONNECTION` to Redis leaves the SQL `jobs` table sitting there, empty
and harmless.

## Running the tests

They need a real Redis, on purpose: a fake that got `WATCH` subtly wrong would
pass while the thing being proved quietly failed in production. Without a
server they skip — they do not silently pass.

```bash
docker run -d -p 6379:6379 redis:7-alpine
uv run pytest tests -q
CRM_TEST_REDIS_URL=redis://localhost:6399/15 uv run pytest tests -q   # elsewhere
```
