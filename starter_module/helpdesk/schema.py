"""The helpdesk's tables: tickets, and the messages in each ticket's thread."""

from __future__ import annotations

from app.schema import Instant, metadata, timestamps
from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)

#: A support ticket: a request from outside the organisation, or one a staff
#: member raised on somebody's behalf, tracked from receipt through to close.
#:
#: ``reference`` is what a ticket is quoted by -- a subject tag, a sentence
#: read over the phone -- because a primary key is not a thing anyone says out
#: loud with confidence they will be understood. It is filled in by
#: :class:`app.providers.sequence.SequencingProvider` immediately after the
#: insert that reveals the primary key it is derived from.
#:
#: ``notified_assignee`` and ``reminded_at`` mirror ``tasks``, for the same
#: reason: ``crm helpdesk-sweep`` announces a hand-over and a ticket ageing
#: past a threshold by comparing columns rather than hooking the write, so
#: every creation and assignment path -- the form, an inline edit, the ingest
#: branch this table is already shaped for -- is covered by one sweep instead
#: of a notification remembered at each of them.
#:
#: ``thread_message_id`` is the anchor a reply threads onto: the Message-ID of
#: whichever message, inbound or outbound, was added to the ticket most
#: recently, so the next outbound reply's In-Reply-To and References point at
#: what was actually said last rather than at the first message forever.
tickets = Table(
    "tickets", metadata,
    Column("id", Integer, primary_key=True),
    Column("reference", String(20), index=True),
    Column("subject", String(200), nullable=False),
    Column("requester_name", String(160)),
    Column("requester_email", String(160), nullable=False, index=True),
    Column("state", String(20), nullable=False, default="new", server_default="new",
           index=True),
    Column("priority", String(20), default="normal", index=True),
    # Who is on it, as the identifier notifications are addressed to, plus the
    # name to show -- the same shape as `tasks.assignee`. Assignment is manual
    # here too: nothing here picks an assignee.
    Column("assignee", String(160), index=True),
    Column("assignee_name", String(160)),
    # "staff" is the only value this branch ever writes; the ingest branch
    # writes "email". The column exists now so that branch's migration is
    # adding rows, not altering a table that already has live ones.
    Column("source", String(20), nullable=False, default="staff", server_default="staff",
           index=True),
    Column("thread_message_id", String(255)),
    Column("created_by", String(160)),
    Column("created_by_name", String(160)),
    Column("notified_assignee", String(160)),
    Column("reminded_at", Instant),
    *timestamps(),
    # The board's grouping query and the sweep's only query: open tickets,
    # oldest first.
    Index("ix_tickets_open", "state", "created_at"),
)

#: What was said to, or received from, the requester -- and only that.
#:
#: An internal remark ("waiting on billing to confirm the refund") belongs in
#: ``timeline_entries``, the activity panel every other record already gets,
#: not here. That is the separation that matters most about this table: there
#: is nothing in its shape -- no flag, no visibility column -- that a private
#: remark could be filed under by mistake. A row here *is*, by definition,
#: something that was or can be emailed to the customer; the only way to keep
#: a remark private is to write it somewhere else, which is exactly what the
#: notes panel is for.
#:
#: ``message_id`` carries a unique constraint now, on a table this branch
#: never writes a duplicate into, because the ingest branch dedupes an
#: at-least-once mail fetch against it and a constraint added after that
#: branch has real rows would be a migration that can fail on the data it
#: exists to protect.
ticket_messages = Table(
    "ticket_messages", metadata,
    Column("id", Integer, primary_key=True),
    Column("ticket_id", Integer, ForeignKey("tickets.id"), nullable=False, index=True),
    Column("direction", String(10), nullable=False, index=True),
    Column("author", String(160)),
    Column("body", Text, nullable=False),
    Column("message_id", String(255), unique=True),
    Column("in_reply_to", String(255)),
    Column("references", Text),
    Column("sent_at", Instant),
    Column("received_at", Instant),
    *timestamps(),
    # The thread's only query: one ticket's messages, in the order they were
    # written.
    Index("ix_ticket_messages_thread", "ticket_id", "created_at"),
)

TABLES = (tickets, ticket_messages)
