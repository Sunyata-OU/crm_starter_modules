"""Turning a support mailbox into tickets and replies.

The decisions are :mod:`starter_module.helpdesk.logic`'s (which ticket does this belong to,
have we seen it, what row does it become); the reading is
:mod:`starter_module.helpdesk.mailbox`'s. This module is only the loop that joins them.

**Stateless on purpose.** There is no "last UID" to lose or corrupt. Each run
looks at the messages of the last few days and skips every one whose
Message-ID is already stored in ``ticket_messages`` -- the same dedupe that
makes running it twice harmless makes a crash half way harmless, and it keeps
working when somebody else reads the mailbox (and flips its seen flags) too.

What becomes of a message:

* **A reply to a ticket** (its ``[T-1042]`` subject tag, or failing that a
  Message-ID in ``In-Reply-To``/``References`` that we stored) is added to that
  ticket's thread. A ticket somebody had resolved, closed or parked as waiting
  comes back to ``open``: the customer answered, so it is news again.
* **Anything else** opens a new ticket, ``source="email"``.
* **A system talking** -- bounce, out-of-office, list mail, or one of our own
  addresses -- is skipped, never stored. Answering those is how two autoresponders
  keep each other busy forever.
"""

from __future__ import annotations

import logging
from collections.abc import Collection, Iterable, Sequence
from datetime import timedelta
from typing import Any

from app.core.clock import utcnow
from app.core.query import Condition, ListQuery, Op
from app.core.results import Ctx, Record

from . import logic as helpdesk
from .mailbox import InboundMail, Mailbox, parse_mail

log = logging.getLogger("crm.helpdesk.ingest")

#: States a customer's reply puts back to ``open``.
REOPEN = ("resolved", "closed", "pending")

_CHUNK = 200

COUNTS = ("new_tickets", "replies", "duplicates", "automatic", "failed")


async def _known(messages: Any, ids: Sequence[str], ctx: Ctx) -> set[str]:
    """Which of these Message-IDs are already stored."""
    found: set[str] = set()
    for start in range(0, len(ids), _CHUNK):
        chunk = list(ids[start:start + _CHUNK])
        page = await messages.provider.list(
            ListQuery(filter=Condition("message_id", Op.IN, chunk), page_size=len(chunk),
                      with_total=False),
            ctx,
        )
        found.update(str(r.get("message_id")) for r in page.items if r.get("message_id"))
    return found


async def _ticket_by_reference(tickets: Any, reference: str, ctx: Ctx) -> Record | None:
    page = await tickets.provider.list(
        ListQuery(filter=Condition("reference", Op.EQ, reference), page_size=1, with_total=False),
        ctx,
    )
    items = list(page.items)
    return items[0] if items else None


async def _ticket_by_thread(tickets: Any, messages: Any, mail: InboundMail, ctx: Ctx) -> Record | None:
    ids = helpdesk.thread_ids(mail.in_reply_to, mail.references)
    if not ids:
        return None
    page = await messages.provider.list(
        ListQuery(filter=Condition("message_id", Op.IN, ids), page_size=1, with_total=False), ctx,
    )
    items = list(page.items)
    if not items:
        return None
    return await tickets.provider.get(items[0].get("ticket_id"), ctx)


def _author(mail: InboundMail) -> str:
    return f"{mail.sender_name} <{mail.sender_email}>" if mail.sender_name else mail.sender_email


async def _store(tickets: Any, messages: Any, mail: InboundMail, ctx: Ctx) -> str:
    """Add one message to its ticket, opening the ticket if there is none. Returns what happened."""
    found: Record | None = None
    reference = helpdesk.match_reference(mail.subject)
    if reference:
        found = await _ticket_by_reference(tickets, reference, ctx)
    if found is None:
        found = await _ticket_by_thread(tickets, messages, mail, ctx)

    opened = found is None
    if found is None:
        made = await tickets.provider.create(
            helpdesk.new_ticket_fields(
                subject=mail.subject or "(no subject)",
                requester_name=mail.sender_name or mail.sender_email,
                requester_email=mail.sender_email,
            ),
            ctx,
        )
        if not made.ok or made.record is None:
            raise RuntimeError(made.message or "The ticket could not be created.")
        ticket = made.record
    else:
        ticket = found

    written = await messages.provider.create(
        helpdesk.new_message_fields(
            ticket_id=ticket.pk, direction=helpdesk.IN, author=_author(mail), body=mail.body,
            message_id=mail.message_id, in_reply_to=mail.in_reply_to, references=mail.references,
            received_at=mail.received_at or utcnow(),
        ),
        ctx,
    )
    if not written.ok:
        raise RuntimeError(written.message or "The message could not be stored.")

    changes: dict[str, Any] = {
        "thread_message_id": helpdesk.next_thread_anchor(
            ticket.get("thread_message_id"), mail.message_id),
    }
    if not opened and str(ticket.get("state")) in REOPEN:
        changes.update({"state": "open", "reminded_at": None})
    await tickets.provider.update(ticket.pk, changes, ctx)
    return "new_tickets" if opened else "replies"


async def ingest(
    registry: Any,
    mailbox: Mailbox,
    ctx: Ctx | None = None,
    *,
    since_days: int = 7,
    ignore_senders: Collection[str] = (),
    limit: int = 100,
) -> dict[str, int]:
    """Read the recent mail and file it. Safe to run as often as you like."""
    counts = dict.fromkeys(COUNTS, 0)
    tickets = helpdesk.resource_for(registry)
    if tickets is None or not registry.has_resource("ticket_messages"):
        return counts
    messages = registry.resource("ticket_messages")
    ctx = ctx or Ctx.system()
    ignored = {s.strip().lower() for s in ignore_senders if s.strip()}

    since = (utcnow() - timedelta(days=since_days)).date()
    listed = list(await mailbox.headers(since))
    stored = await _known(messages, [m for _, m in listed if m], ctx)

    seen_now: set[str] = set()
    todo: list[tuple[str, str]] = []
    for uid, message_id in listed:
        if message_id and (helpdesk.is_duplicate(message_id, stored) or message_id in seen_now):
            counts["duplicates"] += 1
            continue
        seen_now.add(message_id)
        todo.append((uid, message_id))

    for uid, listed_id in todo[:limit]:
        try:
            mail = parse_mail(await mailbox.fetch(uid))
            # A message with no Message-ID gets a stable made-up one, which is
            # only known now -- so the database has to be asked about it too.
            if not listed_id:
                stored |= await _known(messages, [mail.message_id], ctx)
            if helpdesk.is_duplicate(mail.message_id, stored):
                counts["duplicates"] += 1
                continue
            if mail.automatic or mail.sender_email in ignored or not mail.sender_email:
                counts["automatic"] += 1
                continue
            outcome = await _store(tickets, messages, mail, ctx)
            stored.add(mail.message_id)
            counts[outcome] += 1
        except Exception:  # noqa: BLE001 -- one bad message must not stop the rest
            log.exception("helpdesk ingest: message %s could not be filed", uid)
            counts["failed"] += 1

    if todo[limit:]:
        log.info("helpdesk ingest: %d more message(s) left for the next run", len(todo) - limit)
    if any(counts[k] for k in ("new_tickets", "replies", "failed")):
        log.info("helpdesk ingest: %s", counts)
    return counts


def describe(counts: Iterable[tuple[str, int]] | dict[str, int]) -> str:
    c = dict(counts)
    return (f"{c['new_tickets']} new ticket(s), {c['replies']} repl(y/ies), "
            f"{c['duplicates']} already filed, {c['automatic']} automatic skipped, "
            f"{c['failed']} failed.")
