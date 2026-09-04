"""Database schema for Lead Management module."""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, Table, Text
from app.schema import metadata, timestamps

leads = Table(
    "leads",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(120), nullable=False, index=True),
    Column("email", String(160), nullable=False, index=True),
    Column("company_name", String(160), index=True),
    Column("phone", String(40)),
    Column("source", String(40), default="website", index=True),
    Column("status", String(30), default="new", index=True),
    Column("score", Integer, default=50),
    Column("owner", String(60), index=True),
    Column("notes", Text),
    *timestamps(),
)

TABLES = (leads,)
