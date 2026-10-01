# PostgreSQL Database Provider Guide

`crm-starter` supports PostgreSQL out-of-the-box using **SQLAlchemy 2.0 async engine** and **asyncpg**.

## 🔌 Connection Setup

Add your PostgreSQL connection string in `connections.yaml` or set `POSTGRES_URL` in environment variables:

```yaml
connections:
  db.main:
    type: sql
    url: ${POSTGRES_URL:postgresql+asyncpg://postgres:postgres@localhost:5432/crm_db}
```

### Docker Compose PostgreSQL Example

If running via `docker-compose.yaml`:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: crm_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

---

## 🗄️ Database Migrations with Alembic

When you enable modules in `CRM_MODULES`, Alembic automatically reflects all module tables defined in `schema.py`:

```bash
# Generate a migration script for active module tables
CRM_MODULES=crm_companies,crm_people,sales_deals,crm_activities,documents_attachments uv run crm make-migration "add_starter_modules"

# Apply migrations
CRM_MODULES=crm_companies,crm_people,sales_deals,crm_activities,documents_attachments uv run crm migrate
```
