"""Database schema for Marketing Campaigns module."""

from __future__ import annotations

from sqlalchemy import Column, Integer, Numeric, String, Table, Text
from app.schema import metadata, timestamps

marketing_campaigns = Table(
    "marketing_campaigns",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(160), nullable=False, index=True),
    Column("type", String(40), default="email", index=True),
    Column("status", String(30), default="planning", index=True),
    Column("budget", Numeric(12, 2), default=0),
    Column("actual_cost", Numeric(12, 2), default=0),
    Column("expected_revenue", Numeric(12, 2), default=0),
    Column("owner", String(60), index=True),
    Column("notes", Text),
    *timestamps(),
)

TABLES = (marketing_campaigns,)
