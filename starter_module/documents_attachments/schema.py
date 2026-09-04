"""Database schema for Document Attachments module."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from app.schema import Instant, metadata, timestamps

documents = Table(
    "documents",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(160), nullable=False, index=True),
    Column("category", String(40), default="contract", index=True),
    Column("file_path", Text),
    Column("company_id", Integer, ForeignKey("companies.id"), index=True),
    Column("deal_id", Integer, ForeignKey("sales_deals.id"), index=True),
    Column("owner", String(60), index=True),
    Column("notes", Text),
    *timestamps(),
)

TABLES = (documents,)
