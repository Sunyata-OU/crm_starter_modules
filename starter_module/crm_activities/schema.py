"""Database schema for CRM Activities module."""

from __future__ import annotations

from app.schema import Instant, metadata, timestamps
from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text

activities = Table(
    "crm_activities",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("subject", String(160), nullable=False, index=True),
    Column("kind", String(30), default="call", index=True),
    Column("notes", Text),
    Column("performed_at", Instant),
    Column("company_id", Integer, ForeignKey("companies.id"), index=True),
    Column("person_id", Integer, ForeignKey("company_people.id"), index=True),
    Column("deal_id", Integer, ForeignKey("sales_deals.id"), index=True),
    Column("owner", String(60), index=True),
    *timestamps(),
)

TABLES = (activities,)
