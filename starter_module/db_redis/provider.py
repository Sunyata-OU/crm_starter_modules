"""A provider backed by Redis.

Redis has no query engine, so a provider over it has to decide where the
query language is answered. This one answers it **exactly, in Python**, over a
candidate set that Redis narrows first.

That split is the whole design, and it is worth being precise about because the
alternatives are both worse. Pushing filters into Redis for the cases it can
serve and quietly ignoring the rest returns wrong rows. Refusing to filter at
all and letting the capability shim pull the collection turns a queue with a
backlog into an out-of-memory error.

So: **indexes narrow, Python decides.** Every write maintains a set index for
the fields declared in ``indexed`` and a sorted-set index for those in
``scored``. A read walks the top level of the filter, asks each index what it
can, intersects the answers, and fetches only those rows -- then runs the real
filter over them with :mod:`app.providers.local`, the same code every other
emulated backend uses. Narrowing is therefore an optimisation and never a
correctness question: an index that does not exist costs a wider read, not a
wrong answer.

For the job queue, which is what this exists for, the narrowing is the point.
``status = 'queued' AND run_at <= now`` is one ``SMEMBERS`` intersected with one
``ZRANGEBYSCORE``, so a worker polling a queue with fifty thousand finished jobs
in it reads the handful that are actually due.

Storage layout, for anyone reading the keyspace directly:

    <prefix>:<id>            a JSON object, one record
    <prefix>:__seq           the counter behind generated ids
    <prefix>:__ids           every id, for the unfiltered scan
    <prefix>:idx:<f>:<v>     ids whose field <f> equals <v>
    <prefix>:z:<f>           ids scored by field <f>, for range queries
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.core.clock import UTC_ZONE as UTC
from app.core.errors import ProviderError, TooManyRows
from app.core.query import (
    ALL_OPS,
    AggSpec,
    Condition,
    Filter,
    Group,
    ListQuery,
    Op,
    Page,
)
from app.core.results import Ctx, Record, WriteResult
from app.providers import local
from app.providers.base import BaseProvider, Capabilities, Rows

#: Rows this provider will hold in memory to answer one query. The same bargain
#: the capability shim makes: a bounded answer, or an honest failure.
DEFAULT_MAX_ROWS = 5_000

#: How many ids to step over before concluding the counter is hopeless.
_PK_ATTEMPTS = 100

#: Operators an equality index can answer.
SET_OPS = frozenset({Op.EQ, Op.IN})
#: Operators a sorted-set index can answer.
RANGE_OPS = frozenset({Op.LT, Op.LTE, Op.GT, Op.GTE, Op.BETWEEN})


# -- values ------------------------------------------------------------------
#
# JSON has no datetime, and a queue whose `run_at` comes back as a string
# compares as a string. `"2026-01-02T…" <= datetime(...)` is not a comparison
# anyone wants, and `local` would coerce both to text and answer plausibly and
# wrongly. So types that matter are tagged on the way out and restored on the
# way in.

_DT = "__dt__"
_DATE = "__date__"
_DEC = "__dec__"


def encode(value: Any) -> Any:
    if isinstance(value, datetime):
        return {_DT: value.isoformat()}
    if isinstance(value, date):
        return {_DATE: value.isoformat()}
    if isinstance(value, Decimal):
        return {_DEC: str(value)}
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    return value


def decode(value: Any) -> Any:
    if isinstance(value, dict):
        if _DT in value and len(value) == 1:
            parsed = datetime.fromisoformat(value[_DT])
            # Stored in UTC; a naive value would fail every later comparison
            # against an aware one with a TypeError deep in a filter.
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        if _DATE in value and len(value) == 1:
            return date.fromisoformat(value[_DATE])
        if _DEC in value and len(value) == 1:
            return Decimal(value[_DEC])
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def score_of(value: Any) -> float | None:
    """A sortable number for a sorted-set index, or None if there is not one."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC).timestamp()
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    return None


class RedisProvider(BaseProvider):
    """One collection of records in Redis.

    ``indexed`` and ``scored`` name the fields worth an index. Naming none is
    valid and means every read scans the collection, which is fine for
    something small and is exactly what the row budget is there to catch when
    it is not.
    """

    def __init__(
        self,
        client: Any,
        prefix: str,
        *,
        name: str = "",
        pk_field: str = "id",
        searchable_fields: tuple[str, ...] = (),
        indexed: Sequence[str] = (),
        scored: Sequence[str] = (),
        max_rows: int = DEFAULT_MAX_ROWS,
    ) -> None:
        self.client = client
        self.prefix = prefix.rstrip(":")
        self.name = name or f"redis:{prefix}"
        self.pk_field = pk_field
        self.indexed = tuple(indexed)
        self.scored = tuple(scored)
        self.max_rows = max_rows
        # Everything is answered exactly, so the shim has nothing to add and
        # steps aside. "Answered exactly" is the promise the capability flags
        # make; where the work happens is this module's business, and
        # `crm capabilities` is told the truth by `native_detail` below.
        self.capabilities = Capabilities(
            read=True, write=True, delete=True,
            server_filter=True, server_sort=True, server_search=bool(searchable_fields),
            server_paginate=True, total_count=True, aggregate=True,
            filter_ops=ALL_OPS,
            searchable_fields=searchable_fields,
        )

    # -- keys ---------------------------------------------------------------

    def _key(self, pk: Any) -> str:
        return f"{self.prefix}:{pk}"

    @property
    def _ids_key(self) -> str:
        return f"{self.prefix}:__ids"

    def _set_key(self, field: str, value: Any) -> str:
        return f"{self.prefix}:idx:{field}:{'' if value is None else value}"

    def _zset_key(self, field: str) -> str:
        return f"{self.prefix}:z:{field}"

    # -- reading ------------------------------------------------------------

    async def _rows_for(self, ids: Sequence[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        raw = await self.client.mget([self._key(i) for i in ids])
        rows: list[dict[str, Any]] = []
        for blob in raw:
            if blob is None:
                # An id in an index whose record is gone. Skipped rather than
                # raised: indexes are maintained on a best-effort basis across
                # a crash, and a stale entry should cost nothing.
                continue
            rows.append(decode(json.loads(blob)))
        return rows

    async def _candidates(self, f: Filter | None) -> set[str] | None:
        """Ids that could match, or None for "no idea, read everything".

        Only narrows; never decides. A condition this cannot use is simply not
        used, and the exact filter still runs over whatever comes back.
        """
        if f is None:
            return None
        if isinstance(f, Condition):
            return await self._from_index(f)
        # An OR needs the union of branches, and a NOT needs the complement;
        # both are cheaper to answer by reading and filtering than by trying to
        # be clever with sets that may each be the whole collection.
        if isinstance(f, Group) and f.op == "and":
            narrowed: set[str] | None = None
            for child in f.children:
                got = await self._candidates(child)
                if got is None:
                    continue
                narrowed = got if narrowed is None else (narrowed & got)
                if not narrowed:
                    return set()
            return narrowed
        return None

    async def _from_index(self, cond: Condition) -> set[str] | None:
        if cond.field == self.pk_field and cond.op is Op.EQ:
            return {str(cond.value)}
        if cond.field == self.pk_field and cond.op is Op.IN:
            return {str(v) for v in cond.value}

        if cond.field in self.indexed and cond.op in SET_OPS:
            values = cond.value if cond.op is Op.IN else [cond.value]
            found: set[str] = set()
            for value in values:
                members = await self.client.smembers(self._set_key(cond.field, value))
                found |= {_text(m) for m in members}
            return found

        if cond.field in self.scored and cond.op in RANGE_OPS:
            return await self._from_zset(cond)
        return None

    async def _from_zset(self, cond: Condition) -> set[str] | None:
        low: Any = "-inf"
        high: Any = "+inf"
        if cond.op is Op.BETWEEN:
            first, second = tuple(cond.value)
            low, high = score_of(first), score_of(second)
        elif cond.op in (Op.LT, Op.LTE):
            high = score_of(cond.value)
        else:
            low = score_of(cond.value)
        if low is None or high is None:
            # A bound that has no score -- None, or a string. Not something an
            # index can answer, so do not pretend it narrows anything.
            return None
        # Exclusive bounds are written the way Redis spells them. Slightly wide
        # would still be correct, since Python re-checks, but a range index
        # that quietly ignores strictness is the kind of thing that is right
        # until somebody reuses it for something else.
        if cond.op is Op.LT:
            high = f"({high}"
        if cond.op is Op.GT:
            low = f"({low}"
        members = await self.client.zrangebyscore(self._zset_key(cond.field), low, high)
        return {_text(m) for m in members}

    async def _all_ids(self) -> list[str]:
        return [_text(m) for m in await self.client.smembers(self._ids_key)]

    async def _load(self, q: ListQuery) -> list[dict[str, Any]]:
        candidates = await self._candidates(q.effective_filter)
        if candidates is None:
            ids = await self._all_ids()
            if len(ids) > self.max_rows:
                raise TooManyRows(
                    f"{self.name!r} holds {len(ids)} records and this query narrows to "
                    f"none of them, which is over the {self.max_rows} row budget; index "
                    f"the fields being filtered on, or filter on ones that are indexed",
                    provider=self.name,
                    max_rows=self.max_rows,
                )
        else:
            ids = sorted(candidates)
            if len(ids) > self.max_rows:
                raise TooManyRows(
                    f"{self.name!r} narrowed to {len(ids)} records, over the "
                    f"{self.max_rows} row budget",
                    provider=self.name,
                    max_rows=self.max_rows,
                )
        return await self._rows_for(ids)

    async def list(self, q: ListQuery, ctx: Ctx) -> Page[Record]:
        rows = await self._load(q)
        page = local.run_query(
            rows, q, search_fields=self.capabilities.searchable_fields
        )
        return Page(
            items=self._records(list(page.items)),
            page=page.page,
            page_size=page.page_size,
            total=page.total,
            has_more=page.has_more,
        )

    async def get(self, pk: Any, ctx: Ctx) -> Record | None:
        blob = await self.client.get(self._key(pk))
        if blob is None:
            return None
        return self._record(decode(json.loads(blob)))

    async def aggregate(self, spec: AggSpec, ctx: Ctx) -> Rows:
        rows = await self._load(
            ListQuery(filter=spec.filter, scope=spec.scope, with_total=False)
        )
        return local.run_aggregate(rows, spec)

    # -- writing ------------------------------------------------------------

    @property
    def _seq_key(self) -> str:
        return f"{self.prefix}:__seq"

    async def _next_pk(self) -> int:
        """An id nothing is using.

        ``INCR`` alone is not enough, because records may also arrive with an
        id of their own -- a migration, an import, a test fixture -- and the
        counter knows nothing about those. So the counter is a starting point
        and occupied ids are stepped over, which keeps allocation correct
        however far the counter has drifted.
        """
        for _ in range(_PK_ATTEMPTS):
            pk = int(await self.client.incr(self._seq_key))
            if not await self.client.exists(self._key(pk)):
                return pk
        raise ProviderError(
            f"{self.name}: could not find a free id after {_PK_ATTEMPTS} attempts; "
            f"the id counter at {self._seq_key!r} is far behind the records that exist"
        )

    async def _raise_seq_to(self, pk: Any) -> None:
        """Move the counter past an explicitly-supplied id.

        Best-effort, and it does not need to be better: ``_next_pk`` steps over
        anything occupied, so a lost race here costs an extra INCR rather than
        a collision.
        """
        try:
            value = int(pk)
        except (TypeError, ValueError):
            return  # a non-numeric key; the counter has nothing to say about it
        current = await self.client.get(self._seq_key)
        if current is None or int(current) < value:
            await self.client.set(self._seq_key, value)

    def _index_writes(self, pipe: Any, row: dict[str, Any], *, remove: bool = False) -> None:
        """Add or remove one record's index entries, inside a transaction."""
        pk = str(row.get(self.pk_field))
        for field in self.indexed:
            key = self._set_key(field, row.get(field))
            pipe.srem(key, pk) if remove else pipe.sadd(key, pk)
        for field in self.scored:
            zkey = self._zset_key(field)
            score = score_of(row.get(field))
            if remove or score is None:
                # A field that has become null leaves the range index. Leaving
                # it at a stale score is how a job that was rescheduled keeps
                # turning up in the old window.
                pipe.zrem(zkey, pk)
            else:
                pipe.zadd(zkey, {pk: score})
        pipe.srem(self._ids_key, pk) if remove else pipe.sadd(self._ids_key, pk)

    async def _store(self, row: dict[str, Any], previous: dict[str, Any] | None) -> None:
        pk = str(row.get(self.pk_field))
        pipe = self.client.pipeline(transaction=True)
        if previous is not None:
            # Remove the old index entries first: a changed value must not
            # leave the record in the set for its former one.
            self._index_writes(pipe, previous, remove=True)
        pipe.set(self._key(pk), json.dumps(encode(row)))
        self._index_writes(pipe, row)
        await pipe.execute()

    async def create(self, data: dict[str, Any], ctx: Ctx) -> WriteResult:
        row = dict(data)
        supplied = row.get(self.pk_field) not in (None, "")
        if not supplied:
            row[self.pk_field] = await self._next_pk()
        elif await self.client.exists(self._key(row[self.pk_field])):
            return WriteResult.failure(f"a record with id {row[self.pk_field]!r} already exists")
        await self._store(row, None)
        if supplied:
            await self._raise_seq_to(row[self.pk_field])
        return WriteResult.success(self._record(row))

    async def update(self, pk: Any, data: dict[str, Any], ctx: Ctx) -> WriteResult:
        existing = await self.get(pk, ctx)
        if existing is None:
            return WriteResult.failure(f"no record with id {pk!r}")
        previous = existing.as_dict()
        row = {**previous, **data}
        row[self.pk_field] = previous[self.pk_field]
        await self._store(row, previous)
        return WriteResult.success(self._record(row))

    async def update_if(
        self, pk: Any, data: dict[str, Any], expect: dict[str, Any], ctx: Ctx
    ) -> WriteResult | None:
        """Write only while the stored record still matches ``expect``.

        This is the operation the job queue is built on: it is what stops two
        workers claiming the same job, so it has to be a real compare-and-set
        rather than a read followed by a write.

        ``WATCH`` makes Redis abort the transaction if the key changed after we
        read it, and an aborted ``EXEC`` returns ``None`` -- which is exactly
        the "somebody else got there first" the contract asks for. The loser
        gets ``None``, not an error and not a silent overwrite.
        """
        key = self._key(pk)
        async with self.client.pipeline(transaction=True) as pipe:
            try:
                await pipe.watch(key)
                blob = await pipe.get(key)
                if blob is None:
                    await pipe.unwatch()
                    return None
                previous = decode(json.loads(blob))
                for field, wanted in expect.items():
                    if previous.get(field) != wanted:
                        await pipe.unwatch()
                        return None

                row = {**previous, **data}
                row[self.pk_field] = previous[self.pk_field]
                pipe.multi()
                self._index_writes(pipe, previous, remove=True)
                pipe.set(key, json.dumps(encode(row)))
                self._index_writes(pipe, row)
                try:
                    await pipe.execute()
                except Exception as exc:
                    if _is_watch_error(exc):
                        # Somebody wrote to the key between the read and the
                        # commit. Losing the race is the documented answer.
                        return None
                    raise
                return WriteResult.success(self._record(row))
            except ProviderError:
                raise
            except Exception as exc:
                if _is_watch_error(exc):
                    return None
                raise ProviderError(f"conditional write to {self.name} failed: {exc}") from exc

    async def delete(self, pk: Any, ctx: Ctx) -> WriteResult:
        existing = await self.get(pk, ctx)
        if existing is None:
            return WriteResult.failure(f"no record with id {pk!r}")
        row = existing.as_dict()
        pipe = self.client.pipeline(transaction=True)
        self._index_writes(pipe, row, remove=True)
        pipe.delete(self._key(pk))
        await pipe.execute()
        return WriteResult.success(existing)

    # -- lifecycle ----------------------------------------------------------

    async def health(self) -> tuple[bool, str]:
        try:
            await self.client.ping()
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"
        count = await self.client.scard(self._ids_key)
        return True, f"reachable, {count} record(s) under {self.prefix!r}"

    def native_detail(self) -> str:
        """What `crm capabilities` should not be allowed to imply.

        The flags say every query stage is answered here rather than by the
        shim, which is true. This says how, because "native" next to a Redis
        provider would otherwise read as "Redis filtered it", and it did not.
        """
        indexes = ", ".join([*self.indexed, *(f"{f} (range)" for f in self.scored)])
        return (
            f"answered in-process over a candidate set from Redis; "
            f"indexes: {indexes or 'none'}"
        )


def _text(value: Any) -> str:
    return value.decode() if isinstance(value, (bytes, bytearray)) else str(value)


def _is_watch_error(exc: Exception) -> bool:
    """Whether an exception means "the key changed under us".

    Matched by name rather than by class so this module does not import
    ``redis`` at definition time, which is what keeps it optional.
    """
    return type(exc).__name__ in ("WatchError", "ExecAbortError")
