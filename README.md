# CRM Starter Modules (`starter-module`)

A comprehensive modular extension package for **CRM Starter** containing PostgreSQL and Redis backend support, Companies, People/Contacts, Sales Deals Pipeline with Kanban, Activity Logs, Document Storage, Lead Management, Products & Quotes, a Helpdesk, a Keycloak staff roster with impersonation, Contracts & Subscriptions, Marketing Campaigns, and Time Tracking.

> Tasks are no longer a module here: `core_tasks` ships with the framework and
> replaces `todo_actions`. The old `customer_support` is replaced by `helpdesk`.

## 📦 Shipped Modules Suite

| Module | Description | Entry Point Key |
| --- | --- | --- |
| `db_postgres` | PostgreSQL connection pool and provider initialization helper | `db_postgres` |
| `db_redis` | A `redis` connection type and provider — for the [job queue](docs/redis.md) or any resource | `db_redis` |
| `crm_companies` | Company & Organization master data | `crm_companies` |
| `crm_people` | Individual contacts and personnel linked to companies | `crm_people` |
| `sales_deals` | Sales opportunity pipeline with stages and **Pipeline Kanban** | `sales_deals` |
| `crm_activities` | Call, email, meeting, and note logging tied to records | `crm_activities` |
| `documents_attachments` | File upload tracking and document storage | `documents_attachments` |
| `lead_management` | Inbound lead qualification and **Lead Conversion Action** | `lead_management` |
| `products_quotes` | Product catalog SKUs and quotation status pipeline | `products_quotes` |
| `helpdesk` | Support tickets: a board, a customer-visible thread per ticket, a sweep, and the seam an inbound-mail branch plugs into | `helpdesk` |
| `keycloak_accounts` | The staff roster from a Keycloak realm, and signing in as an account with a log of who did | `keycloak_accounts` |
| `contracts_subscriptions` | SaaS recurring revenue (MRR), SLA contracts, and renewal tracking | `contracts_subscriptions` |
| `marketing_campaigns` | Campaign budgeting and **Revenue ROI Chart View** | `marketing_campaigns` |
| `time_tracking` | Client billable hours and timesheet logging | `time_tracking` |

---

## ⚙️ Installation & Usage

1. **Install into your `crm_starter` environment**:
   ```bash
   cd /path/to/crm_starter
   uv pip install -e /path/to/crm_starter_modules

   # db_redis needs a client; every other module is dependency-free.
   uv pip install -e '/path/to/crm_starter_modules[redis]'
   ```

2. **Enable desired modules via `CRM_MODULES` environment variable**:
   ```bash
   # Enable all 14 starter modules:
   CRM_MODULES=db_postgres,db_redis,crm_companies,crm_people,sales_deals,crm_activities,documents_attachments,lead_management,products_quotes,helpdesk,contracts_subscriptions,marketing_campaigns,time_tracking uv run crm dev
   ```

3. **Run database migrations and seed data**:
   ```bash
   CRM_MODULES=crm_companies,crm_people,sales_deals,crm_activities,documents_attachments,lead_management,products_quotes,helpdesk,contracts_subscriptions,marketing_campaigns,time_tracking uv run crm migrate
   CRM_MODULES=crm_companies,crm_people,sales_deals,crm_activities,documents_attachments,lead_management,products_quotes,helpdesk,contracts_subscriptions,marketing_campaigns,time_tracking uv run crm seed
   ```

---

## 🎛️ How to Pick & Choose Modules

Every module in this repository sets `"optional": True` in its `MANIFEST`. Unselected modules remain disabled and will not register tables or views.

Simply pass the modules you want in `CRM_MODULES`:
```bash
# Example: Only load Companies, Deals, and Customer Support
CRM_MODULES=crm_companies,sales_deals,helpdesk uv run crm dev
```

---

## 🧪 Tests

Only `db_redis` has tests today, and they run against a **real Redis** rather
than a fake — what the provider relies on is `WATCH`/`MULTI` aborting a
transaction when the key moved, and a fake that got that subtly wrong would
pass the suite while the thing it proves (that two workers cannot claim the
same job) quietly failed in production.

```bash
docker run -d -p 6379:6379 redis:7-alpine
uv pip install -e '.[redis]' pytest pytest-asyncio
uv run pytest tests -q
```

Without a server the suite **skips**. It does not silently pass.
