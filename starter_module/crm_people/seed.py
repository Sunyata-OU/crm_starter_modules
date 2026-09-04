"""Seed script for People module."""

from __future__ import annotations

from app.schema import get_engine

from starter_module.crm_people.schema import people

SAMPLE_PEOPLE = [
    {
        "id": 1,
        "name": "Sarah Connor",
        "email": "sarah@acme.example.com",
        "phone": "+1 415 555 0100",
        "title": "CTO",
        "company_id": 1,
        "status": "active",
        "owner": "admin@example.com",
        "is_primary": True,
        "notes": "Technical decision maker.",
    },
    {
        "id": 2,
        "name": "Jan Van Dam",
        "email": "jan@globallogistics.example.com",
        "phone": "+31 10 555 0200",
        "title": "VP Operations",
        "company_id": 2,
        "status": "active",
        "owner": "manager@example.com",
        "is_primary": True,
        "notes": "Prefers email contact.",
    },
    {
        "id": 3,
        "name": "Dr. Alice Vance",
        "email": "alice@apexhealth.example.com",
        "phone": "+1 617 555 0300",
        "title": "Head of Research",
        "company_id": 3,
        "status": "lead",
        "owner": "kim@example.com",
        "is_primary": False,
        "notes": "Inquired at conference.",
    },
]


async def seed(ctx=None) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SAMPLE_PEOPLE:
            await conn.execute(
                people.insert().values(**item).prefix_with("OR IGNORE")
            )
