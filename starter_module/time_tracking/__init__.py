"""Time Tracking & Billable Hours Module."""

from __future__ import annotations

from app.core.query import Agg, Measure
from app.core.registry import Registry
from app.fields.types import (
    BooleanField,
    CurrencyField,
    DateField,
    RelationField,
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
    "name": "time_tracking",
    "label": "Time Tracking",
    "description": "Log billable hours, project timesheets, and client work.",
    "depends": ("core_identity",),
    "menu_groups": {"Workspace": 5},
    "optional": True,
}


def register(registry: Registry) -> None:
    registry.add_resource(_time_logs())


def _time_logs() -> Resource:
    return Resource(
        "time_tracking",
        provider="db.main#time_logs",
        label="Time Log",
        label_plural="Time Logs",
        icon="⏱",
        menu_group="Workspace",
        menu_order=50,
        display_field="description",
        default_sort=["-id"],
        policy=DbPolicy(owner_field="logged_by", identity_attr="email"),
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("description", label="Work Summary", required=True, searchable=True, inline_editable=True),
            TextField("hours", label="Hours", required=True, inline_editable=True),
            BooleanField("billable", label="Billable", default=True, inline_editable=True, in_filter=True),
            CurrencyField("hourly_rate", label="Rate ($/hr)", inline_editable=True),
            DateField("log_date", label="Date", in_filter=True, inline_editable=True),
            RelationField("company_id", label="Company", resource="companies", display="name", in_filter=True),
            RelationField("deal_id", label="Deal", resource="sales_deals", display="name", in_filter=True),
            TextField("logged_by", label="Logged By", in_filter=True, inline_editable=True),
        ],
        search=SearchSpec(fields=("description", "logged_by"), filters=("billable", "company_id", "logged_by")),
        views=[
            ListView(
                columns=[
                    Column("description", link=True, width="35%"),
                    "hours",
                    "billable",
                    "hourly_rate",
                    "log_date",
                    "company_id",
                    "logged_by",
                ],
                default_sort=["-id"],
            ),
            ChartView(
                group_by="logged_by",
                measure=Measure(Agg.SUM, "hours", alias="total_hours"),
                label="Hours Logged by User",
                chart="column",
            ),
            FormView(
                sections=[
                    Section("Log Details", fields=["description", "hours", "billable", "hourly_rate", "log_date"]),
                    Section("Links", fields=["company_id", "deal_id", "logged_by"]),
                ]
            ),
            DetailView(
                sections=[
                    Section("Overview", fields=["description", "hours", "billable", "hourly_rate", "log_date"]),
                    Section("Links", fields=["company_id", "deal_id", "logged_by"]),
                ]
            ),
        ],
    )
