"""Database schema for People / Contacts module."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, Text
from app.schema import Instant, metadata, timestamps

people = Table(
    "company_people",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(120), nullable=False, index=True),
    Column("email", String(160), nullable=False, index=True),
    Column("phone", String(40)),
    Column("title", String(120)),
    Column("company_id", Integer, ForeignKey("companies.id"), index=True),
    Column("status", String(20), default="active", index=True),
    Column("owner", String(60), index=True),
    Column("is_primary", Boolean, default=False),
    Column("notes", Text),
    Column("last_contacted", Instant),
    *timestamps(),
)

TABLES = (people,)
