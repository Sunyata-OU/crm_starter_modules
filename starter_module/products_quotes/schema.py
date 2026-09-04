"""Database schema for Products & Quotes module."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Table, Text
from app.schema import metadata, timestamps

products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("sku", String(60), nullable=False, unique=True, index=True),
    Column("name", String(160), nullable=False, index=True),
    Column("unit_price", Numeric(12, 2), default=0),
    Column("category", String(60), default="Software", index=True),
    Column("is_active", Boolean, default=True),
    Column("description", Text),
    *timestamps(),
)

quotes = Table(
    "sales_quotes",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("quote_number", String(60), nullable=False, index=True),
    Column("title", String(160), nullable=False, index=True),
    Column("status", String(30), default="draft", index=True),
    Column("total_amount", Numeric(12, 2), default=0),
    Column("valid_until", String(20), index=True),
    Column("company_id", Integer, ForeignKey("companies.id"), index=True),
    Column("deal_id", Integer, ForeignKey("sales_deals.id"), index=True),
    Column("owner", String(60), index=True),
    Column("notes", Text),
    *timestamps(),
)

TABLES = (products, quotes)
