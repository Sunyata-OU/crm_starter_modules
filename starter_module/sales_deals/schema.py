"""Database schema for Sales Deals module."""

from __future__ import annotations

from app.schema import Instant, metadata, timestamps
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Table, Text

deals = Table(
    "sales_deals",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(160), nullable=False, index=True),
    Column("stage", String(30), default="qualifying", index=True),
    Column("amount", Numeric(12, 2), default=0),
    Column("probability", Integer, default=20),
    Column("expected_close", String(20), index=True),
    Column("closed_on", String(20)),
    Column("company_id", Integer, ForeignKey("companies.id"), index=True),
    Column("person_id", Integer, ForeignKey("company_people.id"), index=True),
    Column("owner", String(60), index=True),
    Column("notes", Text),
    *timestamps(),
)

TABLES = (deals,)
