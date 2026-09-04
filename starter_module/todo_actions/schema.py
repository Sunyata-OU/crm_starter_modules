"""Database schema for Todo Actions module."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from app.schema import Instant, metadata, timestamps

todo_actions = Table(
    "todo_actions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(200), nullable=False, index=True),
    Column("description", Text),
    Column("status", String(20), default="pending", index=True),
    Column("priority", String(20), default="medium", index=True),
    Column("due_date", String(20), index=True),
    Column("company_id", Integer, ForeignKey("companies.id"), index=True),
    Column("person_id", Integer, ForeignKey("company_people.id"), index=True),
    Column("assigned_to", String(60), index=True),
    Column("owner", String(60), index=True),
    Column("completed_at", Instant),
    *timestamps(),
)

TABLES = (todo_actions,)
