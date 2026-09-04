"""Database schema for Companies module."""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, Table, Text
from app.schema import metadata, timestamps

companies = Table(
    "companies",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(160), nullable=False, index=True),
    Column("website", String(255)),
    Column("domain", String(100), index=True),
    Column("industry", String(60), index=True),
    Column("size", String(20)),
    Column("city", String(80)),
    Column("country", String(80)),
    Column("owner", String(60), index=True),
    Column("notes", Text),
    *timestamps(),
)

TABLES = (companies,)
