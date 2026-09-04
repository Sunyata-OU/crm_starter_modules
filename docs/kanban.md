# Kanban Board & Views

`crm-starter` provides declarative **Kanban Board Views** (`BoardView`), allowing users to manage tasks, stages, and workflows visually.

## 📋 Declarative Kanban Configuration

A Kanban board is declared directly on a `Resource` definition:

```python
from app.resources.views import BoardView, Card

BoardView(
    group_by="status",        # The field used for Kanban column swimlanes
    card=Card(
        title="title",        # Card title field
        subtitle="company_id",# Card subtitle / relation link
        badges=["priority", "due_date", "assigned_to"], # Visual badges on card footer
    ),
    default_sort=["due_date"],
    label="Kanban Task Board",
)
```

---

## 🚀 Shipped Kanban Boards

### 1. Todo Actions Kanban (`todo_actions`)
- **Group By**: `status` (`pending`, `in_progress`, `completed`, `cancelled`)
- **Card Content**: Displays task title, associated company name, priority badge (`urgent`, `high`, `medium`, `low`), due date, and assigned user.
- **Interactions**: Drag & drop cards between columns updates `status` automatically in the backend.

### 2. Sales Pipeline Kanban (`sales_deals`)
- **Group By**: `stage` (`qualifying`, `proposal`, `negotiation`, `won`, `lost`)
- **Card Content**: Displays deal title, company name, deal amount, and win probability percentage.
- **Column Aggregations**: Calculates column total revenue (`sum_field="amount"`).
