"""Seed script for Customer Support module."""

from __future__ import annotations

from app.schema import get_engine

from starter_module.customer_support.schema import support_tickets

SAMPLE_TICKETS = [
    {
        "id": 1,
        "ticket_number": "TICK-2026-001",
        "subject": "PostgreSQL connection pool timeout under load",
        "description": "Observed high latency during peak batch processing window.",
        "status": "in_progress",
        "priority": "high",
        "category": "technical",
        "company_id": 1,
        "person_id": 1,
        "assigned_to": "admin@example.com",
        "owner": "sarah@acme.example.com",
    },
    {
        "id": 2,
        "ticket_number": "TICK-2026-002",
        "subject": "Request for custom Kanban view export to CSV",
        "description": "User requesting bulk CSV download for board status lanes.",
        "status": "open",
        "priority": "medium",
        "category": "feature_request",
        "company_id": 2,
        "person_id": 2,
        "assigned_to": "manager@example.com",
        "owner": "jan@globallogistics.example.com",
    },
]


async def seed(ctx=None) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SAMPLE_TICKETS:
            await conn.execute(
                support_tickets.insert().values(**item).prefix_with("OR IGNORE")
            )
