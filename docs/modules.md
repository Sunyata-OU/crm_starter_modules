# Modules Reference

This guide details the internal structure, field definitions, relationships, and actions for each module in `starter-module`.

---

## 1. `db_postgres` (PostgreSQL Database Provider)

- **Purpose**: Integrates PostgreSQL via `asyncpg` + SQLAlchemy connection pool.
- **Provider String**: `db.main#<table_name>`
- **Configuration**:
  ```yaml
  connections:
    db.main:
      type: sql
      url: postgresql+asyncpg://postgres:postgres@localhost:5432/crm_db
  ```

---

## 1b. `db_redis` (Redis Provider)

- **Purpose**: Adds a `redis` connection type and provider. Built for the
  background job queue, but usable by any resource.
- **Provider String**: `redis.<name>#<collection>`
- **Install**: `uv pip install 'crm-starter-modules[redis]'`
- **Configuration**:
  ```yaml
  connections:
    redis.jobs:
      type: redis
      url: ${CRM_REDIS_JOBS_URL:-redis://localhost:6379/1}
      prefix: crm:jobs
      indexed: [status, kind, key, claimed_by]
      scored: [run_at, priority, created_at, finished_at]
  ```
  ```bash
  CRM_MODULES=db_redis CRM_JOBS_CONNECTION=redis.jobs uv run crm worker
  ```
- **How queries work**: indexes narrow the candidate set, Python decides the
  answer — so an index that does not exist costs a wider read, never a wrong
  row. Bounded by `max_rows`, and refused rather than truncated beyond it.
- **`update_if`** is a real compare-and-set on `WATCH`/`MULTI`, which is what
  lets several workers share a queue safely.
- **Durability**: weaker than a database. See [the guide](redis.md#durability-read-this-before-moving-the-queue).

---

## 2. `crm_companies` (Companies Master Data)

- **Resource**: `companies`
- **Fields**:
  - `name` (TextField, required, searchable, inline editable)
  - `website` (URLField)
  - `domain` (TextField, searchable)
  - `industry` (SelectField: Software, Financial services, Healthcare, Manufacturing, Retail, etc.)
  - `size` (SelectField: 1–50, 51–500, 500+)
  - `city`, `country` (TextField)
  - `owner` (TextField, RBAC scoped)
  - `notes` (TextAreaField)

---

## 3. `crm_people` (People & Contacts)

- **Resource**: `people`
- **Fields**:
  - `name` (TextField, required)
  - `email` (EmailField, required)
  - `phone` (PhoneField)
  - `title` (TextField)
  - `company_id` (RelationField -> `companies`)
  - `status` (StatusField: `lead`, `active`, `dormant`, `churned`)
  - `is_primary` (BooleanField)
  - `owner` (TextField)

---

## 4. `todo_actions` (Todo Actions & Kanban)

- **Resource**: `todo_actions`
- **Fields**:
  - `title` (TextField, required)
  - `status` (StatusField: `pending`, `in_progress`, `completed`, `cancelled`)
  - `priority` (StatusField: `low`, `medium`, `high`, `urgent`)
  - `due_date` (DateField)
  - `company_id` (RelationField -> `companies`)
  - `person_id` (RelationField -> `people`)
  - `assigned_to` (TextField)
  - `completed_at` (DateTimeField)
- **Views**: List View, **Kanban BoardView** (grouped by `status`).
- **Actions**: `mark_completed` (stamps `status="completed"` and `completed_at`).

---

## 5. `sales_deals` (Sales Pipeline & Deals)

- **Resource**: `sales_deals`
- **Fields**:
  - `name` (TextField, required)
  - `stage` (StatusField: `qualifying`, `proposal`, `negotiation`, `won`, `lost`)
  - `amount` (CurrencyField)
  - `probability` (PercentField)
  - `expected_close` (DateField)
  - `closed_on` (DateField)
  - `company_id` (RelationField -> `companies`)
  - `person_id` (RelationField -> `people`)
  - `owner` (TextField)
- **Views**: List View, **Pipeline Kanban BoardView** (grouped by `stage`, sum field `amount`), **Chart View** (value by stage).
- **Actions**: `mark_won`, `mark_lost`.

---

## 6. `crm_activities` (Activity Log)

- **Resource**: `crm_activities`
- **Fields**:
  - `subject` (TextField, required)
  - `kind` (SelectField: `call`, `meeting`, `email`, `note`)
  - `company_id` (RelationField -> `companies`)
  - `person_id` (RelationField -> `people`)
  - `deal_id` (RelationField -> `sales_deals`)
  - `owner` (TextField)
  - `notes` (TextAreaField)

---

## 7. `documents_attachments` (Document Storage)

- **Resource**: `documents_attachments`
- **Fields**:
  - `title` (TextField, required)
  - `category` (SelectField: `contract`, `proposal`, `invoice`, `nda`, `other`)
  - `file_path` (FileField)
  - `company_id` (RelationField -> `companies`)
  - `deal_id` (RelationField -> `sales_deals`)
  - `owner` (TextField)
