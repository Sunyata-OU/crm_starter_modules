"""Seed script for Sales Deals module."""

from __future__ import annotations

from datetime import date, timedelta
from app.schema import get_engine
from starter_module.sales_deals.schema import deals

today = date.today()

SAMPLE_DEALS = [
    {
        "id": 1,
        "name": "Acme Enterprise License & Support",
        "stage": "negotiation",
        "amount": 75000.00,
        "probability": 80,
        "expected_close": (today + timedelta(days=14)).isoformat(),
        "company_id": 1,
        "person_id": 1,
        "owner": "admin@example.com",
        "notes": "Contract review currently with legal team.",
    },
    {
        "id": 2,
        "name": "Global Logistics Fleet Fleet Tracking Integration",
        "stage": "proposal",
        "amount": 120000.00,
        "probability": 50,
        "expected_close": (today + timedelta(days=30)).isoformat(),
        "company_id": 2,
        "person_id": 2,
        "owner": "manager@example.com",
        "notes": "RFP response submitted successfully.",
    },
    {
        "id": 3,
        "name": "Apex Health Pilot Implementation",
        "stage": "qualifying",
        "amount": 25000.00,
        "probability": 20,
        "expected_close": (today + timedelta(days=45)).isoformat(),
        "company_id": 3,
        "person_id": 3,
        "owner": "kim@example.com",
        "notes": "Initial discovery meeting scheduled.",
    },
]


async def seed(ctx=None) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SAMPLE_DEALS:
            await conn.execute(
                deals.insert().values(**item).prefix_with("OR IGNORE")
            )
