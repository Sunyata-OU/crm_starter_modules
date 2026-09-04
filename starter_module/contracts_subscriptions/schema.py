"""Database schema for Contracts & Subscriptions module."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Table, Text
from app.schema import metadata, timestamps

contracts = Table(
    "contracts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("contract_number", String(60), nullable=False, index=True),
    Column("title", String(160), nullable=False, index=True),
    Column("status", String(30), default="active", index=True),
    Column("contract_type", String(40), default="annual_license", index=True),
    Column("mrr", Numeric(12, 2), default=0),
    Column("start_date", String(20), index=True),
    Column("end_date", String(20), index=True),
    Column("auto_renew", Boolean, default=True),
    Column("company_id", Integer, ForeignKey("companies.id"), index=True),
    Column("deal_id", Integer, ForeignKey("sales_deals.id"), index=True),
    Column("owner", String(60), index=True),
    Column("notes", Text),
    *timestamps(),
)

TABLES = (contracts,)
