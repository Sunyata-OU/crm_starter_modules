"""Lead Management & Qualification Module."""

from __future__ import annotations

from app.core.registry import Registry
from app.core.results import Ctx
from app.fields.types import (
    EmailField,
    PhoneField,
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
    "name": "lead_management",
    "label": "Leads & Qualification",
    "description": "Capture inbound leads and convert qualified leads to companies & contacts.",
    "depends": ("core_identity",),
    "menu_groups": {"Sales": 15},
    "optional": True,
}

STATUSES = [
    ("new", "New", "blue"),
    ("contacted", "Contacted", "amber"),
    ("qualified", "Qualified", "green"),
    ("disqualified", "Disqualified", "red"),
]

SOURCES = [
    ("website", "Website"),
    ("referral", "Referral"),
    ("webinar", "Webinar"),
    ("event", "Event"),
    ("cold_outreach", "Cold Outreach"),
]


@action(
    "convert_lead",
    "Convert Lead",
    style="primary",
    icon="⚡",
    confirm="Convert this lead into a Company and Person?",
    available=lambda record, identity: record.get("status") != "disqualified",
)
async def convert_lead(records, ctx: Ctx, resource: Resource) -> ActionResult:
    registry = resource.registry
    converted_count = 0

    for r in records:
        company_id = None
        if registry and registry.has_resource("companies") and r.get("company_name"):
            companies = registry.resource("companies")
            comp_res = await companies.provider.create(
                {
                    "name": r.get("company_name"),
                    "owner": ctx.identity.email,
                    "notes": f"Converted from lead {r.get('name')}",
                },
                ctx,
            )
            company_id = comp_res.pk

        if registry and registry.has_resource("people"):
            people = registry.resource("people")
            await people.provider.create(
                {
                    "name": r.get("name"),
                    "email": r.get("email"),
                    "phone": r.get("phone"),
                    "company_id": company_id,
                    "owner": ctx.identity.email,
                    "status": "active",
                },
                ctx,
            )

        await resource.provider.update(r.pk, {"status": "qualified"}, ctx)
        converted_count += 1

    return ActionResult(message=f"Successfully converted {converted_count} lead(s).")


def register(registry: Registry) -> None:
    registry.add_resource(_leads())


def _leads() -> Resource:
    return Resource(
        "leads",
        provider="db.main#leads",
        label="Lead",
        label_plural="Leads",
        icon="🎯",
        menu_group="Sales",
        menu_order=5,
        display_field="name",
        default_sort=["-id"],
        timeline=True,
        policy=DbPolicy(owner_field="owner", identity_attr="email"),
        actions=[convert_lead],
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("name", label="Full Name", required=True, searchable=True, inline_editable=True),
            EmailField("email", label="Email", required=True, searchable=True, inline_editable=True),
            TextField("company_name", label="Company Name", searchable=True, inline_editable=True),
            PhoneField("phone", label="Phone", searchable=True),
            SelectField("source", choices=SOURCES, default="website", in_filter=True, inline_editable=True),
            StatusField("status", choices=STATUSES, default="new", in_filter=True, inline_editable=True),
            TextField("owner", label="Owner", in_filter=True, inline_editable=True),
            TextAreaField("notes", label="Notes", rows=3),
        ],
        search=SearchSpec(
            fields=("name", "email", "company_name", "notes"),
            filters=("status", "source", "owner"),
        ),
        views=[
            ListView(
                columns=[
                    Column("name", link=True, width="25%"),
                    "email",
                    "company_name",
                    "source",
                    "status",
                    "owner",
                ],
                default_sort=["-id"],
                row_actions=["convert_lead"],
            ),
            BoardView(
                group_by="status",
                card=Card(
                    title="name",
                    subtitle="company_name",
                    badges=["source", "email"],
                ),
                default_sort=["-id"],
                label="Lead Qualification Kanban",
            ),
            FormView(
                sections=[
                    Section("Lead Contact", fields=["name", "email", "company_name", "phone"]),
                    Section("Qualification & Owner", fields=["source", "status", "owner"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
            DetailView(
                sections=[
                    Section("Overview", fields=["name", "email", "company_name", "phone", "source", "status", "owner"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
        ],
    )
