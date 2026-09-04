"""Todo Actions & Kanban Module."""

from __future__ import annotations

from datetime import date

from app.core.clock import utcnow
from app.core.query import Condition, Op, and_
from app.core.registry import Registry
from app.core.results import Ctx
from app.fields.types import (
    DateField,
    DateTimeField,
    RelationField,
    SelectField,
    StatusField,
    TextAreaField,
    TextField,
)
from app.resources.actions import ActionResult, action
from app.resources.rbac import DbPolicy
from app.resources.resource import Resource
from app.resources.views import (
    BoardView,
    Card,
    Column,
    DetailView,
    FormView,
    ListView,
    QuickFilter,
    SearchSpec,
    Section,
)

MANIFEST = {
    "name": "todo_actions",
    "label": "Todo Actions & Kanban",
    "description": "Action items and Kanban task board linked to companies and people.",
    "depends": ("core_identity",),
    "menu_groups": {"Workspace": 5},
    "optional": True,
}

STATUSES = [
    ("pending", "Pending", "amber"),
    ("in_progress", "In Progress", "blue"),
    ("completed", "Completed", "green"),
    ("cancelled", "Cancelled", "default"),
]

PRIORITIES = [
    ("low", "Low", "default"),
    ("medium", "Medium", "blue"),
    ("high", "High", "amber"),
    ("urgent", "Urgent", "red"),
]


@action(
    "mark_completed",
    "Mark Completed",
    style="primary",
    icon="✓",
    available=lambda record, identity: record.get("status") != "completed",
)
async def mark_completed(records, ctx: Ctx, resource: Resource) -> ActionResult:
    now_str = utcnow().isoformat()
    for r in records:
        await resource.provider.update(
            r.pk, {"status": "completed", "completed_at": now_str}, ctx
        )
    return ActionResult(message=f"Marked {len(records)} action(s) as completed.")


def register(registry: Registry) -> None:
    registry.add_resource(_todo_actions())


def _todo_actions() -> Resource:
    return Resource(
        "todo_actions",
        provider="db.main#todo_actions",
        label="Todo Action",
        label_plural="Todo Actions",
        icon="✓",
        menu_group="Workspace",
        menu_order=10,
        display_field="title",
        default_sort=["due_date"],
        timeline=True,
        policy=DbPolicy(owner_field="assigned_to", identity_attr="email"),
        actions=[mark_completed],
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("title", label="Action Title", required=True, searchable=True, inline_editable=True),
            StatusField("status", choices=STATUSES, default="pending", in_filter=True, inline_editable=True),
            StatusField("priority", choices=PRIORITIES, default="medium", in_filter=True, inline_editable=True),
            DateField("due_date", label="Due Date", in_filter=True, inline_editable=True),
            RelationField("company_id", label="Company", resource="companies", display="name", in_filter=True),
            RelationField("person_id", label="Person", resource="people", display="name", in_filter=True),
            TextField("assigned_to", label="Assigned To", in_filter=True, inline_editable=True),
            TextField("owner", label="Creator", in_filter=True),
            DateTimeField("completed_at", label="Completed At", readonly=True, in_form=False),
            TextAreaField("description", label="Description", rows=4),
        ],
        search=SearchSpec(
            fields=("title", "description", "assigned_to"),
            filters=("status", "priority", "company_id", "person_id", "assigned_to"),
            quick_filters=[
                QuickFilter(
                    "mine",
                    "Assigned to Me",
                    icon="◉",
                    build=lambda identity: Condition("assigned_to", Op.EQ, identity.email),
                ),
                QuickFilter(
                    "open",
                    "Open Tasks",
                    icon="⏳",
                    build=lambda identity: Condition("status", Op.IN, ["pending", "in_progress"]),
                ),
                QuickFilter(
                    "urgent",
                    "Urgent & High Priority",
                    icon="🔥",
                    build=lambda identity: Condition("priority", Op.IN, ["high", "urgent"]),
                ),
            ],
        ),
        views=[
            ListView(
                columns=[
                    Column("title", link=True, width="30%"),
                    "status",
                    "priority",
                    "due_date",
                    "company_id",
                    "assigned_to",
                ],
                default_sort=["due_date"],
                row_actions=["mark_completed"],
                bulk_actions=["mark_completed", "delete"],
            ),
            BoardView(
                group_by="status",
                card=Card(
                    title="title",
                    subtitle="company_id",
                    badges=["priority", "due_date", "assigned_to"],
                ),
                default_sort=["due_date"],
                label="Kanban Task Board",
            ),
            FormView(
                sections=[
                    Section("Action Info", fields=["title", "status", "priority", "due_date"]),
                    Section("Links & Assignment", fields=["company_id", "person_id", "assigned_to"]),
                    Section("Details", fields=["description"]),
                ]
            ),
            DetailView(
                sections=[
                    Section("Overview", fields=["title", "status", "priority", "due_date", "completed_at"]),
                    Section("Relations & Owner", fields=["company_id", "person_id", "assigned_to", "owner"]),
                    Section("Description", fields=["description"]),
                ]
            ),
        ],
    )
