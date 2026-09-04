"""Marketing Campaigns Module."""

from __future__ import annotations

from app.core.query import Agg, Measure
from app.core.registry import Registry
from app.fields.types import (
    CurrencyField,
    SelectField,
    StatusField,
    TextAreaField,
    TextField,
)
from app.resources.rbac import DbPolicy
from app.resources.resource import Resource
from app.resources.views import (
    ChartView,
    Column,
    DetailView,
    FormView,
    ListView,
    SearchSpec,
    Section,
)

MANIFEST = {
    "name": "marketing_campaigns",
    "label": "Marketing Campaigns",
    "description": "Outbound marketing, campaign budgeting, and ROI tracking.",
    "depends": ("core_identity",),
    "menu_groups": {"Workspace": 5},
    "optional": True,
}

STATUSES = [
    ("planning", "Planning", "default"),
    ("active", "Active", "blue"),
    ("completed", "Completed", "green"),
    ("cancelled", "Cancelled", "red"),
]

TYPES = [
    ("email", "Email Blast"),
    ("webinar", "Webinar"),
    ("event", "Trade Event"),
    ("social", "Social Media"),
]


def register(registry: Registry) -> None:
    registry.add_resource(_campaigns())


def _campaigns() -> Resource:
    return Resource(
        "marketing_campaigns",
        provider="db.main#marketing_campaigns",
        label="Campaign",
        label_plural="Campaigns",
        icon="📣",
        menu_group="Workspace",
        menu_order=40,
        display_field="name",
        default_sort=["-id"],
        timeline=True,
        policy=DbPolicy(owner_field="owner", identity_attr="email"),
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("name", label="Campaign Name", required=True, searchable=True, inline_editable=True),
            SelectField("type", choices=TYPES, default="email", in_filter=True),
            StatusField("status", choices=STATUSES, default="planning", in_filter=True, inline_editable=True),
            CurrencyField("budget", label="Budget", inline_editable=True),
            CurrencyField("actual_cost", label="Actual Cost", inline_editable=True),
            CurrencyField("expected_revenue", label="Expected Revenue", inline_editable=True),
            TextField("owner", label="Owner", in_filter=True, inline_editable=True),
            TextAreaField("notes", label="Notes", rows=3),
        ],
        search=SearchSpec(fields=("name", "notes"), filters=("type", "status", "owner")),
        views=[
            ListView(
                columns=[
                    Column("name", link=True, width="30%"),
                    "type",
                    "status",
                    "budget",
                    "actual_cost",
                    "expected_revenue",
                    "owner",
                ],
                default_sort=["-id"],
            ),
            ChartView(
                group_by="type",
                measure=Measure(Agg.SUM, "expected_revenue", alias="total_expected_revenue"),
                label="Revenue Forecast by Campaign Type",
                chart="column",
            ),
            FormView(
                sections=[
                    Section("Campaign Info", fields=["name", "type", "status", "owner"]),
                    Section("Financials", fields=["budget", "actual_cost", "expected_revenue"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
            DetailView(
                sections=[
                    Section("Overview", fields=["name", "type", "status", "owner"]),
                    Section("Financial Performance", fields=["budget", "actual_cost", "expected_revenue"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
        ],
    )
