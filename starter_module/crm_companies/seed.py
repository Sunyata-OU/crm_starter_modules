"""Seed script for Companies module."""

from __future__ import annotations

from app.schema import get_engine

from starter_module.crm_companies.schema import companies

SAMPLE_COMPANIES = [
    {
        "id": 1,
        "name": "Acme Technologies",
        "website": "https://acme.example.com",
        "domain": "acme.example.com",
        "industry": "Software",
        "size": "51–500",
        "city": "San Francisco",
        "country": "USA",
        "owner": "admin@example.com",
        "notes": "Key enterprise account in software sector.",
    },
    {
        "id": 2,
        "name": "Global Logistics Corp",
        "website": "https://globallogistics.example.com",
        "domain": "globallogistics.example.com",
        "industry": "Transportation",
        "size": "500+",
        "city": "Rotterdam",
        "country": "Netherlands",
        "owner": "manager@example.com",
        "notes": "Large supply chain operator.",
    },
    {
        "id": 3,
        "name": "Apex Health Systems",
        "website": "https://apexhealth.example.com",
        "domain": "apexhealth.example.com",
        "industry": "Healthcare",
        "size": "1–50",
        "city": "Boston",
        "country": "USA",
        "owner": "kim@example.com",
        "notes": "Medical device manufacturer looking for upgrade.",
    },
]


async def seed(ctx=None) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SAMPLE_COMPANIES:
            await conn.execute(
                companies.insert().values(**item).prefix_with("OR IGNORE")
            )
