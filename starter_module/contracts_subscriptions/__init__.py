"""Contracts & Subscriptions Module."""

from __future__ import annotations

from datetime import date, timedelta

from app.core.registry import Registry
from app.core.results import Ctx
from app.fields.types import (
    BooleanField,
    CurrencyField,
    DateField,
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
    Column,
    DetailView,
    FormView,
    ListView,
    SearchSpec,
    Section,
)

MANIFEST = {
    "name": "contracts_subscriptions",
    "label": "Contracts & Subscriptions",
    "description": "Recurring SaaS revenue, SLA contracts, and renewal tracking.",
    "depends": ("core_identity",),
    "menu_groups": {"Sales": 15},
    "optional": True,
}

STATUSES = [
    ("active", "Active", "green"),
    ("pending_renewal", "Pending Renewal", "amber"),
    ("expired", "Expired", "red"),
    ("cancelled", "Cancelled", "default"),
]

TYPES = [
    ("annual_license", "Annual License"),
    ("monthly_subscription", "Monthly Subscription"),
    ("retainer", "Service Retainer"),
]


@action(
    "renew_contract",
    "Extend 1 Year",
    style="primary",
    icon="↻",
    available=lambda record, identity: record.get("status") in ("active", "pending_renewal"),
)
async def renew_contract(records, ctx: Ctx, resource: Resource) -> ActionResult:
    for r in records:
        current_end = r.get("end_date")
        try:
            base_date = date.fromisoformat(current_end) if current_end else date.today()
        except ValueError:
            base_date = date.today()
        new_end = (base_date + timedelta(days=365)).isoformat()
        await resource.provider.update(r.pk, {"status": "active", "end_date": new_end}, ctx)
    return ActionResult(message=f"Extended {len(records)} contract(s) by 1 year.")


def register(registry: Registry) -> None:
    registry.add_resource(_contracts())


def _contracts() -> Resource:
    return Resource(
        "contracts",
        provider="db.main#contracts",
        label="Contract",
        label_plural="Contracts",
        icon="📄",
        menu_group="Sales",
        menu_order=50,
        display_field="title",
        default_sort=["-id"],
        timeline=True,
        policy=DbPolicy(owner_field="owner", identity_attr="email"),
        actions=[renew_contract],
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("contract_number", label="Contract #", required=True, searchable=True, inline_editable=True),
            TextField("title", label="Title", required=True, searchable=True, inline_editable=True),
            StatusField("status", choices=STATUSES, default="active", in_filter=True, inline_editable=True),
            SelectField("contract_type", choices=TYPES, default="annual_license", in_filter=True),
            CurrencyField("mrr", label="MRR ($)", inline_editable=True),
            DateField("start_date", label="Start Date", in_filter=True, inline_editable=True),
            DateField("end_date", label="End Date", in_filter=True, inline_editable=True),
            BooleanField("auto_renew", label="Auto Renew", default=True, inline_editable=True),
            RelationField("company_id", label="Company", resource="companies", display="name", in_filter=True),
            RelationField("deal_id", label="Deal", resource="sales_deals", display="name", in_filter=True),
            TextField("owner", label="Owner", in_filter=True, inline_editable=True),
            TextAreaField("notes", label="Notes", rows=3),
        ],
        search=SearchSpec(
            fields=("contract_number", "title", "notes"),
            filters=("status", "contract_type", "company_id", "owner"),
        ),
        views=[
            ListView(
                columns=[
                    Column("contract_number", width="15%"),
                    Column("title", link=True, width="30%"),
                    "status",
                    "mrr",
                    "end_date",
                    "company_id",
                    "owner",
                ],
                default_sort=["-id"],
                row_actions=["renew_contract"],
            ),
            FormView(
                sections=[
                    Section("Contract Terms", fields=["contract_number", "title", "status", "contract_type", "mrr"]),
                    Section("Dates & Renewals", fields=["start_date", "end_date", "auto_renew"]),
                    Section("Links & Owner", fields=["company_id", "deal_id", "owner"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
            DetailView(
                sections=[
                    Section("Overview", fields=["contract_number", "title", "status", "contract_type", "mrr"]),
                    Section("Dates", fields=["start_date", "end_date", "auto_renew"]),
                    Section("Links", fields=["company_id", "deal_id", "owner"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
        ],
    )
