"""Seed script for Products & Quotes module."""

from __future__ import annotations

from datetime import date, timedelta

from app.schema import get_engine

from starter_module.products_quotes.schema import products, quotes

today = date.today()

SAMPLE_PRODUCTS = [
    {
        "id": 1,
        "sku": "ENT-SUB-01",
        "name": "Enterprise CRM Subscription (Annual)",
        "unit_price": 50000.00,
        "category": "Software",
        "is_active": True,
        "description": "Full platform access with unlimited seats and Postgres provider support.",
    },
    {
        "id": 2,
        "sku": "IMP-SVC-01",
        "name": "Implementation & Migration Package",
        "unit_price": 15000.00,
        "category": "Services",
        "is_active": True,
        "description": "Custom data migration, schema setup, and user onboarding.",
    },
]

SAMPLE_QUOTES = [
    {
        "id": 1,
        "quote_number": "Q-2026-001",
        "title": "Acme Enterprise License & Onboarding Quote",
        "status": "sent",
        "total_amount": 65000.00,
        "valid_until": (today + timedelta(days=30)).isoformat(),
        "company_id": 1,
        "deal_id": 1,
        "owner": "admin@example.com",
        "notes": "Includes 1 year support SLA.",
    },
]


async def seed(ctx=None) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SAMPLE_PRODUCTS:
            await conn.execute(
                products.insert().values(**item).prefix_with("OR IGNORE")
            )
        for item in SAMPLE_QUOTES:
            await conn.execute(
                quotes.insert().values(**item).prefix_with("OR IGNORE")
            )
