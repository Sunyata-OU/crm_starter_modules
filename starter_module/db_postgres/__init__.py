"""PostgreSQL Provider configuration helper module.

Ensures PostgreSQL database integration is properly recognized by the application.
PostgreSQL connections can be defined in `connections.yaml` or via standard environment variables:

```yaml
connections:
  db.main:
    type: sql
    url: ${POSTGRES_URL:postgresql+asyncpg://postgres:postgres@localhost:5432/crm_db}
```
"""

from __future__ import annotations

from app.core.registry import Registry

MANIFEST = {
    "name": "db_postgres",
    "label": "PostgreSQL Database Provider",
    "description": "Configures PostgreSQL backed storage via asyncpg and SQLAlchemy.",
    "depends": (),
    "optional": True,
}


def register(registry: Registry) -> None:
    # SQLProvider handles PostgreSQL backend queries automatically for all declared tables.
    pass
