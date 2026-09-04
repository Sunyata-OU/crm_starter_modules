# CRM Starter Modules (`starter-module`)

A modular extension package for **CRM Starter** containing PostgreSQL backend support, Companies, People/Contacts, Todo Actions with Kanban, Sales Deals Pipeline with Kanban, Activity Logs, and Document Storage.

## 📦 What Ships in This Repository

| Module | Description | Entry Point Key |
| --- | --- | --- |
| `db_postgres` | PostgreSQL connection pool and provider initialization helper | `db_postgres` |
| `crm_companies` | Company & Organization master data | `crm_companies` |
| `crm_people` | Individual contacts and personnel linked to companies | `crm_people` |
| `todo_actions` | Action items with priority, due dates, and **Kanban Board** | `todo_actions` |
| `sales_deals` | Sales opportunity pipeline with stages and **Pipeline Kanban** | `sales_deals` |
| `crm_activities` | Call, email, meeting, and note logging tied to records | `crm_activities` |
| `documents_attachments` | File upload tracking and document storage | `documents_attachments` |

---

## ⚙️ Installation & Usage

1. **Install into your `crm_starter` environment**:
   ```bash
   cd /path/to/crm_starter
   uv pip install -e /path/to/crm_starter_modules
   ```

2. **Enable desired modules via `CRM_MODULES` environment variable**:
   ```bash
   # Enable all starter modules:
   CRM_MODULES=db_postgres,crm_companies,crm_people,todo_actions,sales_deals,crm_activities,documents_attachments uv run crm dev
   ```

3. **Run database migrations and seed data**:
   ```bash
   CRM_MODULES=crm_companies,crm_people,todo_actions,sales_deals,crm_activities,documents_attachments uv run crm migrate
   CRM_MODULES=crm_companies,crm_people,todo_actions,sales_deals,crm_activities,documents_attachments uv run crm seed
   ```

---

## 🎛️ How to Pick & Choose Modules

You have two ways to select which modules to install and use:

### Method A: Environment Variable Selection (Recommended)
Every module in this repository sets `"optional": True` in its `MANIFEST`. Unselected modules remain disabled and will not register tables or views.

Simply pass the modules you want in `CRM_MODULES`:
```bash
# Example: Only load Companies and Todo Actions with Kanban
CRM_MODULES=crm_companies,todo_actions uv run crm dev
```

### Method B: Deleting Module Directories
If you want to physically strip unwanted modules from this repository:
1. Delete the module subdirectory (e.g. remove `starter_module/sales_deals`).
2. Remove the entry point from `pyproject.toml`:
   ```toml
   [project.entry-points."crm.modules"]
   # Remove: sales_deals = "starter_module.sales_deals"
   ```
3. Re-install editable package: `uv pip install -e .`

---

## 🐘 PostgreSQL Setup

To use PostgreSQL with `db_postgres`, configure your `connections.yaml` or `.env` in `crm_starter`:

```yaml
connections:
  db.main:
    type: sql
    url: postgresql+asyncpg://postgres:password@localhost:5432/crm_db
```
