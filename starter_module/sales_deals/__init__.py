"""Sales Deals & Pipeline Module."""

from __future__ import annotations

from datetime import date

from app.core.query import Agg, Condition, Measure, Op
from app.core.registry import Registry
from app.core.results import Ctx
from app.fields.types import (
    CurrencyField,
    DateField,
    DateTimeField,
    PercentField,
    RelationField,
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
    ChartView,
    Column,
    DetailView,
    FormView,
    ListView,
    QuickFilter,
    SearchSpec,
    Section,
)

MANIFEST = {
    "name": "sales_deals",
    "label": "Sales Pipeline & Deals",
    "description": "Opportunity pipeline with deal stages, forecasting, and Kanban board.",
    "depends": ("core_identity",),
    "menu_groups": {"Sales": 15},
    "optional": True,
}

STAGES = [
    ("qualifying", "Qualifying", "default"),
    ("proposal", "Proposal", "blue"),
    ("negotiation", "Negotiation", "amber"),
    ("won", "Won", "green"),
    ("lost", "Lost", "red"),
]


@action(
    "mark_won",
    "Mark Won",
    style="primary",
    icon="✓",
    available=lambda record, identity: record.get("stage") not in ("won", "lost"),
)
async def mark_won(records, ctx: Ctx, resource: Resource) -> ActionResult:
    today_str = date.today().isoformat()
    for r in records:
        await resource.provider.update(
            r.pk, {"stage": "won", "probability": 100, "closed_on": today_str}, ctx
        )
    return ActionResult(message=f"Marked {len(records)} deal(s) as won.")


@action(
    "mark_lost",
    "Mark Lost",
    style="danger",
    icon="✕",
    available=lambda record, identity: record.get("stage") not in ("won", "lost"),
)
async def mark_lost(records, ctx: Ctx, resource: Resource) -> ActionResult:
    today_str = date.today().isoformat()
    for r in records:
        await resource.provider.update(
            r.pk, {"stage": "lost", "probability": 0, "closed_on": today_str}, ctx
        )
    return ActionResult(message=f"Marked {len(records)} deal(s) as lost.")


def register(registry: Registry) -> None:
    registry.add_resource(_deals())


def _deals() -> Resource:
    return Resource(
        "sales_deals",
        provider="db.main#sales_deals",
        label="Deal",
        label_plural="Deals",
        icon="◈",
        menu_group="Sales",
        menu_order=10,
        display_field="name",
        default_sort=["-amount"],
        timeline=True,
        policy=DbPolicy(owner_field="owner", identity_attr="email"),
        actions=[mark_won, mark_lost],
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("name", label="Deal Title", required=True, searchable=True, inline_editable=True),
            StatusField("stage", choices=STAGES, default="qualifying", in_filter=True, inline_editable=True),
            CurrencyField("amount", label="Deal Amount", inline_editable=True),
            PercentField("probability", label="Probability %", default=20, inline_editable=True),
            DateField("expected_close", label="Expected Close", in_filter=True, inline_editable=True),
            DateField("closed_on", label="Closed On", readonly=True, in_form=False),
            RelationField("company_id", label="Company", resource="companies", display="name", in_filter=True),
            RelationField("person_id", label="Contact", resource="people", display="name", in_filter=True),
            TextField("owner", label="Owner", in_filter=True, inline_editable=True),
            TextAreaField("notes", label="Notes", rows=3),
        ],
        search=SearchSpec(
            fields=("name", "notes"),
            filters=("stage", "company_id", "owner"),
            quick_filters=[
                QuickFilter(
                    "open",
                    "Active Opportunities",
                    icon="◈",
                    build=lambda identity: Condition("stage", Op.NOT_IN, ["won", "lost"]),
                ),
                QuickFilter(
                    "won",
                    "Closed Won",
                    icon="★",
                    build=lambda identity: Condition("stage", Op.EQ, "won"),
                ),
            ],
        ),
        views=[
            ListView(
                columns=[
                    Column("name", link=True, width="30%"),
                    "amount",
                    "stage",
                    "probability",
                    "expected_close",
                    "company_id",
                    "owner",
                ],
                default_sort=["-amount"],
                row_actions=["mark_won"],
                bulk_actions=["mark_won", "mark_lost", "delete"],
            ),
            BoardView(
                group_by="stage",
                card=Card(
                    title="name",
                    subtitle="company_id",
                    badges=["amount", "probability"],
                ),
                sum_field="amount",
                default_sort=["-amount"],
                label="Sales Pipeline Kanban",
            ),
            ChartView(
                group_by="stage",
                measure=Measure(Agg.SUM, "amount", alias="total_value"),
                label="Pipeline Value by Stage",
                chart="column",
            ),
            FormView(
                sections=[
                    Section("Deal Details", fields=["name", "amount", "stage", "probability", "expected_close"]),
                    Section("Relations & Owner", fields=["company_id", "person_id", "owner"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
            DetailView(
                sections=[
                    Section("Overview", fields=["name", "amount", "stage", "probability", "expected_close", "closed_on"]),
                    Section("Relations", fields=["company_id", "person_id", "owner"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
        ],
    )
