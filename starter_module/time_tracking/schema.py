"""Database schema for Time Tracking module."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Table, Text
from app.schema import metadata, timestamps

time_logs = Table(
    "time_logs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("description", String(200), nullable=False, index=True),
    Column("hours", Numeric(6, 2), default=1.0),
    Column("billable", Boolean, default=True),
    Column("hourly_rate", Numeric(10, 2), default=150.00),
    Column("log_date", String(20), index=True),
    Column("company_id", Integer, ForeignKey("companies.id"), index=True),
    Column("deal_id", Integer, ForeignKey("sales_deals.id"), index=True),
    Column("logged_by", String(60), index=True),
    *timestamps(),
)

TABLES = (time_logs,)
