"""Seed script for CRM Activities module."""

from __future__ import annotations

from app.core.clock import utcnow
from app.schema import get_engine

from starter_module.crm_activities.schema import activities

now = utcnow()

SAMPLE_ACTIVITIES = [
    {
        "id": 1,
        "subject": "Discovery Call with Sarah",
        "kind": "call",
        "notes": "Discussed PostgreSQL migration timelines and support SLA.",
        "company_id": 1,
        "person_id": 1,
        "deal_id": 1,
        "owner": "admin@example.com",
    },
    {
        "id": 2,
        "subject": "Demo Meeting with Jan",
        "kind": "meeting",
        "notes": "Demonstrated custom Kanban task boards and audit logging.",
        "company_id": 2,
        "person_id": 2,
        "deal_id": 2,
        "owner": "manager@example.com",
    },
]


async def seed(ctx=None) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SAMPLE_ACTIVITIES:
            await conn.execute(
                activities.insert().values(**item).prefix_with("OR IGNORE")
            )
