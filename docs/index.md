# CRM Starter Modules Documentation

Welcome to the **CRM Starter Modules** documentation. This repository provides a 13-module enterprise CRM suite designed for the `crm_starter` framework.

## 🚀 Quick Start

### 1. Install the Package
```bash
cd /path/to/crm_starter
uv pip install -e /path/to/crm_starter_modules
```

### 2. Enable Active Modules
```bash
CRM_MODULES=db_postgres,db_redis,crm_companies,crm_people,todo_actions,sales_deals,crm_activities,documents_attachments,lead_management,products_quotes,customer_support,contracts_subscriptions,marketing_campaigns,time_tracking uv run crm dev
```

---

## 🧩 Complete Module Suite

| Module Name | Key Feature | Views Included |
| --- | --- | --- |
| **`db_postgres`** | PostgreSQL DB Provider | Connection Provider |
| **`db_redis`** | [Redis provider](redis.md), for the job queue or any resource | Connection Provider |
| **`crm_companies`** | Company Master Data | List, Form, Detail, Timeline |
| **`crm_people`** | Personnel & Contacts | List, Form, Detail, Timeline |
| **`todo_actions`** | Action Items & Task Kanban | List, **Kanban Board**, Form, Detail |
| **`sales_deals`** | Opportunity Pipeline & Stage Kanban | List, **Pipeline Kanban**, Chart, Detail |
| **`crm_activities`** | Call, Email, Meeting & Note Logs | List, Form, Detail, Timeline |
| **`documents_attachments`** | Document Storage & File Attachments | List, Form, Detail |
| **`lead_management`** | Inbound Lead Qualification & Conversion Action | List, **Kanban Board**, Form, Detail |
| **`products_quotes`** | Product Catalog SKUs & Quotations | List, Form, Detail |
| **`customer_support`** | Helpdesk Ticket Management | List, **Ticket Kanban Board**, Detail |
| **`contracts_subscriptions`** | SaaS Recurring Revenue (MRR) & SLA Tracking | List, Form, Detail, Renewal Action |
| **`marketing_campaigns`** | Outbound Campaigns & Budgeting | List, **ROI Chart View**, Detail |
| **`time_tracking`** | Client Billable Hours & Timesheets | List, **User Hours Chart View**, Detail |
