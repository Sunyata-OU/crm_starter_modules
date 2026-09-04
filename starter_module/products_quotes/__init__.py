"""Products & Quotes Module."""

from __future__ import annotations

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
    "name": "products_quotes",
    "label": "Products & Quotations",
    "description": "Product catalog and sales quotations.",
    "depends": ("core_identity",),
    "menu_groups": {"Sales": 15},
    "optional": True,
}

QUOTE_STATUSES = [
    ("draft", "Draft", "default"),
    ("sent", "Sent", "blue"),
    ("accepted", "Accepted", "green"),
    ("rejected", "Rejected", "red"),
]


@action(
    "send_quote",
    "Mark as Sent",
    style="primary",
    icon="✉",
    available=lambda record, identity: record.get("status") == "draft",
)
async def send_quote(records, ctx: Ctx, resource: Resource) -> ActionResult:
    for r in records:
        await resource.provider.update(r.pk, {"status": "sent"}, ctx)
    return ActionResult(message=f"Marked {len(records)} quote(s) as sent.")


@action(
    "accept_quote",
    "Mark Accepted",
    style="success",
    icon="✓",
    available=lambda record, identity: record.get("status") in ("draft", "sent"),
)
async def accept_quote(records, ctx: Ctx, resource: Resource) -> ActionResult:
    for r in records:
        await resource.provider.update(r.pk, {"status": "accepted"}, ctx)
    return ActionResult(message=f"Marked {len(records)} quote(s) as accepted.")


def register(registry: Registry) -> None:
    registry.add_resource(_products())
    registry.add_resource(_quotes())


def _products() -> Resource:
    return Resource(
        "products",
        provider="db.main#products",
        label="Product",
        label_plural="Products",
        icon="📦",
        menu_group="Sales",
        menu_order=40,
        display_field="name",
        default_sort=["name"],
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("sku", label="SKU", required=True, searchable=True, inline_editable=True),
            TextField("name", label="Product Name", required=True, searchable=True, inline_editable=True),
            CurrencyField("unit_price", label="Unit Price", inline_editable=True),
            SelectField("category", choices=["Software", "Services", "Hardware", "Maintenance"], default="Software", in_filter=True),
            BooleanField("is_active", label="Active", default=True, inline_editable=True),
            TextAreaField("description", label="Description", rows=3),
        ],
        search=SearchSpec(fields=("sku", "name", "description"), filters=("category", "is_active")),
        views=[
            ListView(columns=[Column("sku", width="15%"), Column("name", link=True, width="35%"), "unit_price", "category", "is_active"]),
            FormView(sections=[Section("Product Details", fields=["sku", "name", "unit_price", "category", "is_active"]), Section("Description", fields=["description"])]),
            DetailView(sections=[Section("Overview", fields=["sku", "name", "unit_price", "category", "is_active"]), Section("Description", fields=["description"])]),
        ],
    )


def _quotes() -> Resource:
    return Resource(
        "quotes",
        provider="db.main#sales_quotes",
        label="Quote",
        label_plural="Quotes",
        icon="🧾",
        menu_group="Sales",
        menu_order=45,
        display_field="title",
        default_sort=["-id"],
        actions=[send_quote, accept_quote],
        policy=DbPolicy(owner_field="owner", identity_attr="email"),
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("quote_number", label="Quote #", required=True, searchable=True, inline_editable=True),
            TextField("title", label="Title", required=True, searchable=True, inline_editable=True),
            StatusField("status", choices=QUOTE_STATUSES, default="draft", in_filter=True, inline_editable=True),
            CurrencyField("total_amount", label="Total Amount", inline_editable=True),
            DateField("valid_until", label="Valid Until", in_filter=True, inline_editable=True),
            RelationField("company_id", label="Company", resource="companies", display="name", in_filter=True),
            RelationField("deal_id", label="Deal", resource="sales_deals", display="name", in_filter=True),
            TextField("owner", label="Owner", in_filter=True, inline_editable=True),
            TextAreaField("notes", label="Notes", rows=3),
        ],
        search=SearchSpec(fields=("quote_number", "title", "notes"), filters=("status", "company_id", "owner")),
        views=[
            ListView(columns=[Column("quote_number", width="15%"), Column("title", link=True, width="30%"), "status", "total_amount", "company_id", "owner"]),
            FormView(sections=[Section("Quote Info", fields=["quote_number", "title", "status", "total_amount", "valid_until"]), Section("Links", fields=["company_id", "deal_id", "owner"]), Section("Notes", fields=["notes"])]),
            DetailView(sections=[Section("Overview", fields=["quote_number", "title", "status", "total_amount", "valid_until"]), Section("Links", fields=["company_id", "deal_id", "owner"]), Section("Notes", fields=["notes"])]),
        ],
    )
