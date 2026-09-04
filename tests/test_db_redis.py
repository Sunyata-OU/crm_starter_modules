"""The Redis provider.

Two things are being proved, and only one of them is ordinary.

The ordinary one is that the provider satisfies the query contract: filters,
sorts, pages and counts come back the same as they would from any other
backend. Those assertions are written against the same query language every
provider answers, so they are the contract rather than a description of this
implementation.

The other is that `update_if` is a **real** compare-and-set. Everything the job
queue does rests on it -- it is the only thing standing between two workers and
the same job -- so it is tested under actual contention against an actual
server, not asserted about in a docstring.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from app.core.clock import utcnow
from app.core.errors import TooManyRows
from app.core.query import (
    Agg,
    AggSpec,
    Condition,
    ListQuery,
    Measure,
    Op,
    Sort,
    SortDir,
    and_,
    or_,
)
from app.core.results import Ctx

from starter_module.db_redis import RedisConnection, build_redis_provider

CTX = Ctx.system()


class _Resource:
    """The little the provider factory asks of a resource."""

    name = "widgets"
    pk = "id"

    @staticmethod
    def searchable_fields() -> tuple[str, ...]:
        return ("name", "note")


ROWS = [
    {"id": 1, "name": "Ada",     "stage": "won",  "amount": 5000, "owner": "kim", "note": None},
    {"id": 2, "name": "Grace",   "stage": "won",  "amount": 8200, "owner": "kim", "note": "referral"},
    {"id": 3, "name": "Alan",    "stage": "open", "amount": 3100, "owner": "sam", "note": "inbound"},
    {"id": 4, "name": "Katherine", "stage": "open", "amount": 9900, "owner": "sam", "note": None},
    {"id": 5, "name": "Barbara", "stage": "lost", "amount": 1200, "owner": "kim", "note": "budget"},
]


@pytest.fixture
async def provider(redis_url):
    from redis.asyncio import Redis

    client = Redis.from_url(redis_url, decode_responses=True)
    await client.flushdb()
    handle = RedisConnection(
        client,
        prefix="test",
        indexed=("stage", "owner"),
        scored=("amount", "due_at"),
    )
    built = build_redis_provider(handle, "widgets", _Resource())
    for row in ROWS:
        await built.create(dict(row), CTX)
    try:
        yield built
    finally:
        await client.flushdb()
        await client.aclose()


async def _ids(provider, **kw) -> list:
    page = await provider.list(ListQuery(**kw), CTX)
    return [r.pk for r in page.items]


class TestTheQueryContract:
    """The same questions every other backend answers."""

    @pytest.mark.asyncio
    async def test_everything_comes_back(self, provider):
        assert sorted(await _ids(provider, sort=(Sort("id"),))) == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_an_indexed_equality_filter(self, provider):
        assert await _ids(provider, filter=Condition("stage", Op.EQ, "won"),
                          sort=(Sort("id"),)) == [1, 2]

    @pytest.mark.asyncio
    async def test_an_unindexed_filter_is_still_exact(self, provider):
        """An index that does not exist costs a wider read, not a wrong answer."""
        assert await _ids(provider, filter=Condition("name", Op.ICONTAINS, "ad"),
                          sort=(Sort("id"),)) == [1]

    @pytest.mark.asyncio
    async def test_a_range_on_a_scored_field(self, provider):
        assert await _ids(provider, filter=Condition("amount", Op.GT, 5000),
                          sort=(Sort("id"),)) == [2, 4]

    @pytest.mark.asyncio
    async def test_an_exclusive_bound_is_exclusive(self, provider):
        """The index writes `(` for a strict bound; a wide range would still be
        filtered correctly in Python, which is exactly why this is asserted."""
        assert await _ids(provider, filter=Condition("amount", Op.GTE, 5000),
                          sort=(Sort("id"),)) == [1, 2, 4]
        assert await _ids(provider, filter=Condition("amount", Op.GT, 5000),
                          sort=(Sort("id"),)) == [2, 4]

    @pytest.mark.asyncio
    async def test_an_and_of_two_indexes(self, provider):
        assert await _ids(provider, filter=and_(
            Condition("owner", Op.EQ, "kim"), Condition("amount", Op.GTE, 5000),
        ), sort=(Sort("id"),)) == [1, 2]

    @pytest.mark.asyncio
    async def test_an_or_is_answered_without_narrowing(self, provider):
        """Not something set intersection can do, so it must fall back."""
        assert await _ids(provider, filter=or_(
            Condition("stage", Op.EQ, "lost"), Condition("owner", Op.EQ, "sam"),
        ), sort=(Sort("id"),)) == [3, 4, 5]

    @pytest.mark.asyncio
    async def test_is_null(self, provider):
        assert await _ids(provider, filter=Condition("note", Op.IS_NULL),
                          sort=(Sort("id"),)) == [1, 4]

    @pytest.mark.asyncio
    async def test_search(self, provider):
        assert await _ids(provider, search="referral") == [2]

    @pytest.mark.asyncio
    async def test_sorting_and_paging(self, provider):
        page = await provider.list(
            ListQuery(sort=(Sort("amount", SortDir.DESC),), page=2, page_size=2), CTX
        )
        assert [r.pk for r in page.items] == [1, 3]
        assert page.total == 5

    @pytest.mark.asyncio
    async def test_a_scope_is_applied_like_a_filter(self, provider):
        """Row-level security must not be lost on the way into a new backend."""
        assert await _ids(provider, scope=Condition("owner", Op.EQ, "sam"),
                          sort=(Sort("id"),)) == [3, 4]

    @pytest.mark.asyncio
    async def test_aggregate(self, provider):
        rows = await provider.aggregate(
            AggSpec(group_by=("stage",),
                    measures=(Measure(Agg.COUNT, alias="n"), Measure(Agg.SUM, "amount")),
                    sort=(Sort("stage"),)),
            CTX,
        )
        assert rows == [
            {"stage": "lost", "n": 1, "sum_amount": 1200},
            {"stage": "open", "n": 2, "sum_amount": 13000},
            {"stage": "won", "n": 2, "sum_amount": 13200},
        ]

    @pytest.mark.asyncio
    async def test_get_and_missing_get(self, provider):
        assert (await provider.get(3, CTX))["name"] == "Alan"
        assert await provider.get(999, CTX) is None


class TestWrites:
    @pytest.mark.asyncio
    async def test_create_allocates_a_key(self, provider):
        result = await provider.create({"name": "Radia", "stage": "open"}, CTX)
        assert result.ok and result.record.pk == 6

    @pytest.mark.asyncio
    async def test_update_keeps_the_indexes_in_step(self, provider):
        """The bug this prevents: a record still listed under its old value."""
        await provider.update(1, {"stage": "lost"}, CTX)
        assert await _ids(provider, filter=Condition("stage", Op.EQ, "won")) == [2]
        assert sorted(await _ids(provider, filter=Condition("stage", Op.EQ, "lost"))) == [1, 5]

    @pytest.mark.asyncio
    async def test_a_range_index_follows_a_changed_value(self, provider):
        await provider.update(5, {"amount": 99999}, CTX)
        assert 5 in await _ids(provider, filter=Condition("amount", Op.GT, 50000))

    @pytest.mark.asyncio
    async def test_delete_removes_it_from_every_index(self, provider):
        await provider.delete(2, CTX)
        assert await provider.get(2, CTX) is None
        assert await _ids(provider, filter=Condition("stage", Op.EQ, "won")) == [1]
        assert 2 not in await _ids(provider, sort=(Sort("id"),))

    @pytest.mark.asyncio
    async def test_updating_something_absent_is_reported(self, provider):
        assert (await provider.update(999, {"name": "x"}, CTX)).failed


class TestConditionalWrites:
    """`update_if` is what stops two workers claiming the same job."""

    @pytest.mark.asyncio
    async def test_it_writes_when_the_expectation_holds(self, provider):
        result = await provider.update_if(1, {"stage": "lost"}, {"stage": "won"}, CTX)
        assert result is not None and result.ok
        assert (await provider.get(1, CTX))["stage"] == "lost"

    @pytest.mark.asyncio
    async def test_it_declines_when_it_does_not(self, provider):
        assert await provider.update_if(1, {"stage": "lost"}, {"stage": "open"}, CTX) is None
        assert (await provider.get(1, CTX))["stage"] == "won", "it wrote anyway"

    @pytest.mark.asyncio
    async def test_a_missing_record_declines_rather_than_creating_one(self, provider):
        assert await provider.update_if(999, {"stage": "x"}, {"stage": "y"}, CTX) is None
        assert await provider.get(999, CTX) is None

    @pytest.mark.asyncio
    async def test_exactly_one_of_many_racers_wins(self, provider):
        """The assertion the whole module exists to support.

        Twenty coroutines try to claim the same record with the same
        expectation. Redis arbitrates; nineteen must be told they lost.
        """
        results = await asyncio.gather(*(
            provider.update_if(3, {"owner": f"racer-{i}"}, {"owner": "sam"}, CTX)
            for i in range(20)
        ))
        winners = [r for r in results if r is not None]
        assert len(winners) == 1, f"{len(winners)} racers all thought they won"
        assert (await provider.get(3, CTX))["owner"] == winners[0].record["owner"]


class TestBounds:
    @pytest.mark.asyncio
    async def test_an_unnarrowable_query_over_budget_is_refused(self, redis_url):
        """Refused, not truncated -- the same bargain the shim makes."""
        from redis.asyncio import Redis

        client = Redis.from_url(redis_url, decode_responses=True)
        await client.flushdb()
        handle = RedisConnection(client, prefix="bounded", max_rows=3)
        provider = build_redis_provider(handle, "widgets", _Resource())
        try:
            for row in ROWS:
                await provider.create(dict(row), CTX)
            with pytest.raises(TooManyRows):
                await provider.list(
                    ListQuery(filter=Condition("name", Op.ICONTAINS, "a")), CTX
                )
        finally:
            await client.flushdb()
            await client.aclose()


class TestTypesSurviveTheRoundTrip:
    """JSON has no datetime, and a queue whose `run_at` came back as a string
    would compare as a string -- plausibly, and wrongly."""

    @pytest.mark.asyncio
    async def test_a_datetime_is_still_a_datetime(self, provider):
        when = utcnow()
        await provider.create({"id": 90, "name": "timed", "due_at": when}, CTX)
        got = await provider.get(90, CTX)
        assert got["due_at"] == when

    @pytest.mark.asyncio
    async def test_a_datetime_range_filter_is_correct(self, provider):
        now = utcnow()
        await provider.create({"id": 91, "name": "past", "due_at": now - timedelta(hours=1)}, CTX)
        await provider.create({"id": 92, "name": "future", "due_at": now + timedelta(hours=1)}, CTX)
        due = await _ids(provider, filter=Condition("due_at", Op.LTE, now))
        assert 91 in due and 92 not in due

    @pytest.mark.asyncio
    async def test_a_null_value_leaves_the_range_index(self, provider):
        """A rescheduled job must not keep turning up in its old window."""
        now = utcnow()
        await provider.create({"id": 93, "name": "x", "due_at": now - timedelta(hours=1)}, CTX)
        assert 93 in await _ids(provider, filter=Condition("due_at", Op.LTE, now))
        await provider.update(93, {"due_at": None}, CTX)
        assert 93 not in await _ids(provider, filter=Condition("due_at", Op.LTE, now))


class TestIdAllocation:
    """Records arrive with ids of their own -- an import, a migration, a
    fixture -- and the counter knows nothing about them."""

    @pytest.mark.asyncio
    async def test_a_generated_id_steps_over_an_explicit_one(self, provider):
        """The fixture created 1-5 explicitly; the next generated id must not
        be 1."""
        result = await provider.create({"name": "Radia", "stage": "open"}, CTX)
        assert result.ok, result.message
        assert result.record.pk == 6

    @pytest.mark.asyncio
    async def test_generated_ids_stay_unique_under_concurrency(self, provider):
        results = await asyncio.gather(*(
            provider.create({"name": f"n{i}"}, CTX) for i in range(25)
        ))
        pks = [r.record.pk for r in results if r.ok]
        assert len(pks) == 25, [r.message for r in results if not r.ok]
        assert len(set(pks)) == 25, "two records were given the same id"

    @pytest.mark.asyncio
    async def test_a_duplicate_explicit_id_is_refused(self, provider):
        assert (await provider.create({"id": 1, "name": "clash"}, CTX)).failed
