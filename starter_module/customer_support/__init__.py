"""Customer Support & Helpdesk Module."""

from __future__ import annotations

from app.core.registry import Registry
from app.core.results import Ctx
from app.fields.types import (
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
    SearchSpec,
    Section,
)

MANIFEST = {
    "name": "customer_support",
    "label": "Customer Support Tickets",
    "description": "Post-sales helpdesk, issue tracking, and support ticket Kanban board.",
    "depends": ("core_identity",),
    "menu_groups": {"Support": 25},
    "optional": True,
}

STATUSES = [
    ("open", "Open", "amber"),
    ("in_progress", "In Progress", "blue"),
    ("resolved", "Resolved", "green"),
    ("closed", "Closed", "default"),
]

PRIORITIES = [
    ("low", "Low", "default"),
    ("medium", "Medium", "blue"),
    ("high", "High", "amber"),
    ("urgent", "Urgent", "red"),
]

CATEGORIES = [
    ("technical", "Technical Issue"),
    ("feature_request", "Feature Request"),
    ("billing", "Billing & Account"),
    ("general", "General Inquiry"),
]


@action(
    "resolve_ticket",
    "Mark Resolved",
    style="success",
    icon="✓",
    available=lambda record, identity: record.get("status") in ("open", "in_progress"),
)
async def resolve_ticket(records, ctx: Ctx, resource: Resource) -> ActionResult:
    for r in records:
        await resource.provider.update(r.pk, {"status": "resolved"}, ctx)
    return ActionResult(message=f"Marked {len(records)} ticket(s) as resolved.")


@action(
    "close_ticket",
    "Close Ticket",
    style="secondary",
    icon="✕",
    available=lambda record, identity: record.get("status") != "closed",
)
async def close_ticket(records, ctx: Ctx, resource: Resource) -> ActionResult:
    for r in records:
        await resource.provider.update(r.pk, {"status": "closed"}, ctx)
    return ActionResult(message=f"Closed {len(records)} ticket(s).")


def register(registry: Registry) -> None:
    registry.add_resource(_tickets())


def _tickets() -> Resource:
    return Resource(
        "support_tickets",
        provider="db.main#support_tickets",
        label="Support Ticket",
        label_plural="Support Tickets",
        icon="🎫",
        menu_group="Support",
        menu_order=10,
        display_field="subject",
        default_sort=["-id"],
        timeline=True,
        policy=DbPolicy(owner_field="assigned_to", identity_attr="email"),
        actions=[resolve_ticket, close_ticket],
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("ticket_number", label="Ticket #", required=True, searchable=True, inline_editable=True),
            TextField("subject", label="Subject", required=True, searchable=True, inline_editable=True),
            StatusField("status", choices=STATUSES, default="open", in_filter=True, inline_editable=True),
            StatusField("priority", choices=PRIORITIES, default="medium", in_filter=True, inline_editable=True),
            SelectField("category", choices=CATEGORIES, default="technical", in_filter=True),
            RelationField("company_id", label="Company", resource="companies", display="name", in_filter=True),
            RelationField("person_id", label="Person", resource="people", display="name", in_filter=True),
            TextField("assigned_to", label="Assigned Agent", in_filter=True, inline_editable=True),
            TextField("owner", label="Reporter", in_filter=True),
            TextAreaField("description", label="Description", rows=4),
        ],
        search=SearchSpec(
            fields=("ticket_number", "subject", "description"),
            filters=("status", "priority", "category", "company_id", "assigned_to"),
        ),
        views=[
            ListView(
                columns=[
                    Column("ticket_number", width="15%"),
                    Column("subject", link=True, width="30%"),
                    "status",
                    "priority",
                    "company_id",
                    "assigned_to",
                ],
                default_sort=["-id"],
                row_actions=["resolve_ticket"],
            ),
            BoardView(
                group_by="status",
                card=Card(
                    title="subject",
                    subtitle="company_id",
                    badges=["priority", "ticket_number", "assigned_to"],
                ),
                default_sort=["-id"],
                label="Helpdesk Ticket Kanban",
            ),
            FormView(
                sections=[
                    Section("Ticket Info", fields=["ticket_number", "subject", "status", "priority", "category"]),
                    Section("Assignment & Links", fields=["company_id", "person_id", "assigned_to", "owner"]),
                    Section("Description", fields=["description"]),
                ]
            ),
            DetailView(
                sections=[
                    Section("Overview", fields=["ticket_number", "subject", "status", "priority", "category"]),
                    Section("Assignment", fields=["company_id", "person_id", "assigned_to", "owner"]),
                    Section("Description", fields=["description"]),
                ]
            ),
        ],
    )
