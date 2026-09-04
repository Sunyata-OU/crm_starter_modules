"""Seed script for Time Tracking module."""

from __future__ import annotations

from datetime import date

from app.schema import get_engine

from starter_module.time_tracking.schema import time_logs

today = date.today()

SAMPLE_TIME_LOGS = [
    {
        "id": 1,
        "description": "PostgreSQL database optimization and index tuning",
        "hours": 4.5,
        "billable": True,
        "hourly_rate": 175.00,
        "log_date": today.isoformat(),
        "company_id": 1,
        "deal_id": 1,
        "logged_by": "admin@example.com",
    },
]


async def seed(ctx=None) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SAMPLE_TIME_LOGS:
            await conn.execute(
                time_logs.insert().values(**item).prefix_with("OR IGNORE")
            )
