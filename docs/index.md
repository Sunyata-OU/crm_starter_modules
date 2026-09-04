# CRM Starter Modules

Welcome to the **CRM Starter Modules** documentation. This package is a modular extension suite designed for the `crm_starter` framework.

It provides out-of-the-box business entities, PostgreSQL backend integration, and rich interactive views (including Kanban task boards and sales pipeline boards).

## 🚀 Quick Start

### 1. Install the Package
Install `crm-starter-modules` into your `crm_starter` project environment in editable mode:

```bash
cd /path/to/crm_starter
uv pip install -e /path/to/crm_starter_modules
```

### 2. Enable Modules
Select which modules to activate using the `CRM_MODULES` environment variable:

```bash
CRM_MODULES=db_postgres,crm_companies,crm_people,todo_actions,sales_deals,crm_activities,documents_attachments uv run crm dev
```

### 3. Run Migrations & Seed Data
Generate and apply database tables, then populate initial sample data:

```bash
CRM_MODULES=crm_companies,crm_people,todo_actions,sales_deals,crm_activities,documents_attachments uv run crm migrate
CRM_MODULES=crm_companies,crm_people,todo_actions,sales_deals,crm_activities,documents_attachments uv run crm seed
```

---

## 🧩 Shipped Modules Overview

| Module Name | Description | Views Included |
| --- | --- | --- |
| **`db_postgres`** | PostgreSQL database connection provider helper | Provider integration |
| **`crm_companies`** | Company & Organization master records | List, Form, Detail, Timeline |
| **`crm_people`** | Personnel & Contacts linked to companies | List, Form, Detail, Timeline |
| **`todo_actions`** | Action items with priority, due date & assignment | List, **Kanban Board**, Form, Detail |
| **`sales_deals`** | Revenue opportunities & sales pipeline stages | List, **Pipeline Kanban Board**, Chart, Form, Detail |
| **`crm_activities`** | Call, email, meeting, and note activity logs | List, Form, Detail |
| **`documents_attachments`** | Document management & file attachment storage | List, Form, Detail |

---

## 🎯 Design Principles

- **Zero Coupling**: Every module declares its own resources, SQLAlchemy tables (`schema.py`), and seed scripts (`seed.py`).
- **Pluggable via Entry Points**: Discovered automatically by Python packaging (`crm.modules` entry points).
- **Pick-and-Choose Ready**: Modules are marked `"optional": True`. You can choose which modules to enable via environment settings or physically delete unused folders without breaking the rest of the app.
