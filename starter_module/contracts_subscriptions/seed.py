"""Seed script for Contracts & Subscriptions module."""

from __future__ import annotations

from datetime import date, timedelta

from app.schema import get_engine

from starter_module.contracts_subscriptions.schema import contracts

today = date.today()

SAMPLE_CONTRACTS = [
    {
        "id": 1,
        "contract_number": "CTR-2026-001",
        "title": "Acme Enterprise SLA & SaaS Subscription",
        "status": "active",
        "contract_type": "annual_license",
        "mrr": 6250.00,
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=365)).isoformat(),
        "auto_renew": True,
        "company_id": 1,
        "deal_id": 1,
        "owner": "admin@example.com",
        "notes": "Includes 24/7 dedicated support engineer.",
    },
]


async def seed(ctx=None) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SAMPLE_CONTRACTS:
            await conn.execute(
                contracts.insert().values(**item).prefix_with("OR IGNORE")
            )
