"""Seed script for Marketing Campaigns module."""

from __future__ import annotations

from app.schema import get_engine

from starter_module.marketing_campaigns.schema import marketing_campaigns

SAMPLE_CAMPAIGNS = [
    {
        "id": 1,
        "name": "Q3 Enterprise PostgreSQL Webinar",
        "type": "webinar",
        "status": "completed",
        "budget": 5000.00,
        "actual_cost": 4200.00,
        "expected_revenue": 150000.00,
        "owner": "admin@example.com",
        "notes": "Generated 45 qualified sales leads.",
    },
]


async def seed(ctx=None) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SAMPLE_CAMPAIGNS:
            await conn.execute(
                marketing_campaigns.insert().values(**item).prefix_with("OR IGNORE")
            )
