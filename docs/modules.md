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

---

## 8. `lead_management` (Leads & Qualification)

- **Resource**: `leads` — table `leads`
- **Menu**: Sales
- **Scoping**: `DbPolicy(owner_field="owner")`, so a rep sees their own leads
- **Fields**:
  - `name` (TextField, required, searchable, inline editable)
  - `email` (EmailField, required, searchable)
  - `company_name` (TextField, searchable) — a name, not a relation: an
    unqualified lead has no company record yet
  - `phone` (PhoneField, searchable)
  - `source` (SelectField, filterable)
  - `status` (StatusField, filterable, inline editable)
  - `owner` (TextField, filterable)
  - `notes` (TextAreaField)
- **Views**: List, **Kanban Board** (by status), Form, Detail
- **Action**: `convert_lead` — promotes a qualified lead into a company and a
  contact. Hidden once the lead is disqualified.

---

## 9. `products_quotes` (Products & Quotations)

Two resources, because a catalogue and a quotation have different lifetimes.

- **Resource**: `products` — table `products`
  - `sku` (TextField, required, searchable), `name` (TextField, required,
    searchable), `unit_price` (CurrencyField), `category` (SelectField:
    Software, Services, Hardware, Maintenance), `is_active` (BooleanField),
    `description` (TextAreaField)
  - **Views**: List, Form, Detail
- **Resource**: `quotes` — table **`sales_quotes`**
  - `quote_number`, `title` (TextField, required, searchable), `status`
    (StatusField, filterable), `total_amount` (CurrencyField), `valid_until`
    (DateField, filterable), `company_id` (RelationField -> `companies`),
    `deal_id` (RelationField -> `sales_deals`), `owner`, `notes`
  - **Scoping**: `DbPolicy(owner_field="owner")`
  - **Views**: List, Form, Detail
  - **Actions**: `send_quote` (draft only), `accept_quote` (draft or sent) —
    both gated on the status the transition makes sense from, so an action is
    never offered where it would not apply

---

## 10. `helpdesk` and `keycloak_accounts`

These two ship with their own tables, migrations, templates and settings; see
[`helpdesk.md`](helpdesk.md) and [`keycloak.md`](keycloak.md).

---

## 11. `contracts_subscriptions` (Contracts & Recurring Revenue)

- **Resource**: `contracts` — table `contracts`
- **Menu**: Sales
- **Fields**:
  - `contract_number`, `title` (TextField, required, searchable)
  - `status` (StatusField, filterable, inline editable)
  - `contract_type` (SelectField, filterable)
  - `mrr` (CurrencyField) — monthly recurring revenue
  - `start_date` / `end_date` (DateField, filterable)
  - `auto_renew` (BooleanField)
  - `company_id` (RelationField -> `companies`), `deal_id` (RelationField ->
    `sales_deals`)
  - `owner` (TextField, filterable), `notes` (TextAreaField)
- **Views**: List, Form, Detail
- **Action**: `renew_contract` — offered on active and pending-renewal
  contracts

---

## 12. `marketing_campaigns` (Campaigns & ROI)

- **Resource**: `marketing_campaigns` — table `marketing_campaigns`
- **Menu**: Workspace
- **Fields**:
  - `name` (TextField, required, searchable)
  - `type` (SelectField, filterable) / `status` (StatusField, filterable)
  - `budget`, `actual_cost`, `expected_revenue` (CurrencyField) — the three
    numbers the ROI chart is built from
  - `owner` (TextField, filterable), `notes` (TextAreaField)
- **Views**: List, **ROI Chart**, Form, Detail

---

## 13. `time_tracking` (Billable Hours)

- **Resource**: `time_tracking` — table **`time_logs`**
- **Menu**: Workspace
- **Fields**:
  - `description` (TextField, required, searchable)
  - `hours` (TextField, required) / `hourly_rate` (CurrencyField)
  - `billable` (BooleanField, filterable)
  - `log_date` (DateField, filterable)
  - `company_id` (RelationField -> `companies`), `deal_id` (RelationField ->
    `sales_deals`)
  - `logged_by` (TextField, filterable)
- **Views**: List, **Hours Chart**, Form, Detail

