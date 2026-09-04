"""Seed script for Document Attachments module."""

from __future__ import annotations

from app.schema import get_engine

from starter_module.documents_attachments.schema import documents

SAMPLE_DOCUMENTS = [
    {
        "id": 1,
        "title": "Acme Enterprise SLA Agreement 2026",
        "category": "contract",
        "company_id": 1,
        "deal_id": 1,
        "owner": "admin@example.com",
        "notes": "Signed copy of master services agreement.",
    },
]


async def seed(ctx=None) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SAMPLE_DOCUMENTS:
            await conn.execute(
                documents.insert().values(**item).prefix_with("OR IGNORE")
            )
