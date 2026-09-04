"""Seed script for Todo Actions module."""

from __future__ import annotations

from datetime import date, timedelta
from app.schema import get_engine
from starter_module.todo_actions.schema import todo_actions

today = date.today()

SAMPLE_TODOS = [
    {
        "id": 1,
        "title": "Send technical architecture proposal to Acme",
        "description": "Prepare custom deployment document focusing on PostgreSQL scalability.",
        "status": "in_progress",
        "priority": "high",
        "due_date": (today + timedelta(days=2)).isoformat(),
        "company_id": 1,
        "person_id": 1,
        "assigned_to": "admin@example.com",
        "owner": "admin@example.com",
    },
    {
        "id": 2,
        "title": "Quarterly account check-in call with Jan",
        "description": "Discuss log optimization requirements.",
        "status": "pending",
        "priority": "medium",
        "due_date": (today + timedelta(days=5)).isoformat(),
        "company_id": 2,
        "person_id": 2,
        "assigned_to": "manager@example.com",
        "owner": "manager@example.com",
    },
    {
        "id": 3,
        "title": "Follow up on medical compliance questions",
        "description": "Send security whitepaper to Dr. Vance.",
        "status": "completed",
        "priority": "urgent",
        "due_date": (today - timedelta(days=1)).isoformat(),
        "company_id": 3,
        "person_id": 3,
        "assigned_to": "kim@example.com",
        "owner": "kim@example.com",
    },
]


async def seed(ctx=None) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SAMPLE_TODOS:
            await conn.execute(
                todo_actions.insert().values(**item).prefix_with("OR IGNORE")
            )
