"""Database schema for Customer Support module."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from app.schema import metadata, timestamps

support_tickets = Table(
    "support_tickets",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("ticket_number", String(60), nullable=False, index=True),
    Column("subject", String(160), nullable=False, index=True),
    Column("description", Text),
    Column("status", String(30), default="open", index=True),
    Column("priority", String(20), default="medium", index=True),
    Column("category", String(40), default="general", index=True),
    Column("company_id", Integer, ForeignKey("companies.id"), index=True),
    Column("person_id", Integer, ForeignKey("company_people.id"), index=True),
    Column("assigned_to", String(60), index=True),
    Column("owner", String(60), index=True),
    *timestamps(),
)

TABLES = (support_tickets,)
