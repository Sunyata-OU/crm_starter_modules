"""Seed script for Lead Management module."""

from __future__ import annotations

from app.schema import get_engine
from starter_module.lead_management.schema import leads

SAMPLE_LEADS = [
    {
        "id": 1,
        "name": "Marcus Wright",
        "email": "marcus@cyberdyne.example.com",
        "company_name": "Cyberdyne Systems",
        "phone": "+1 415 555 0199",
        "source": "website",
        "status": "new",
        "score": 85,
        "owner": "admin@example.com",
        "notes": "Inquired about enterprise database integration.",
    },
    {
        "id": 2,
        "name": "Elena Rostova",
        "email": "elena@novatech.example.com",
        "company_name": "NovaTech Solutions",
        "phone": "+44 20 555 0188",
        "source": "webinar",
        "status": "contacted",
        "score": 70,
        "owner": "manager@example.com",
        "notes": "Attended Q3 architecture demo webinar.",
    },
]


async def seed(ctx=None) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SAMPLE_LEADS:
            await conn.execute(
                leads.insert().values(**item).prefix_with("OR IGNORE")
            )
