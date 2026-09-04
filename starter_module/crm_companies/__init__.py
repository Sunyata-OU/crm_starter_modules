"""Companies module declaration."""

from __future__ import annotations

from app.core.registry import Registry
from app.fields.types import (
    SelectField,
    TextAreaField,
    TextField,
    URLField,
)
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
    "name": "crm_companies",
    "label": "Companies",
    "description": "Company and organization master data.",
    "depends": ("core_identity",),
    "menu_groups": {"Records": 10},
    "optional": True,
}

INDUSTRIES = [
    "Software",
    "Financial services",
    "Healthcare",
    "Manufacturing",
    "Retail",
    "Transportation",
    "Education",
    "Other",
]

SIZES = ["1–50", "51–500", "500+"]


def register(registry: Registry) -> None:
    registry.add_resource(_companies())


def _companies() -> Resource:
    return Resource(
        "companies",
        provider="db.main#companies",
        label="Company",
        label_plural="Companies",
        icon="▣",
        menu_group="Records",
        menu_order=10,
        display_field="name",
        default_sort=["name"],
        timeline=True,
        policy=DbPolicy(owner_field="owner", identity_attr="email"),
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("name", label="Company Name", required=True, searchable=True, inline_editable=True, max_length=160),
            URLField("website", label="Website", searchable=True, inline_editable=True),
            TextField("domain", label="Domain", searchable=True, inline_editable=True),
            SelectField("industry", choices=INDUSTRIES, in_filter=True, inline_editable=True),
            SelectField("size", label="Size", choices=SIZES, in_filter=True, inline_editable=True),
            TextField("city", label="City", in_filter=True),
            TextField("country", label="Country", in_filter=True),
            TextField("owner", label="Owner", in_filter=True, inline_editable=True),
            TextAreaField("notes", label="Notes", rows=3),
        ],
        search=SearchSpec(
            fields=("name", "website", "domain", "city", "notes"),
            filters=("industry", "size", "country", "owner"),
        ),
        views=[
            ListView(
                columns=[
                    Column("name", link=True, width="30%"),
                    "industry",
                    "size",
                    "city",
                    "country",
                    "owner",
                ],
                default_sort=["name"],
            ),
            FormView(
                sections=[
                    Section("Company Details", fields=["name", "website", "domain", "industry", "size"]),
                    Section("Location & Owner", fields=["city", "country", "owner"]),
                    Section("Additional Information", fields=["notes"]),
                ]
            ),
            DetailView(
                sections=[
                    Section("Overview", fields=["name", "website", "domain", "industry", "size", "owner"]),
                    Section("Location", fields=["city", "country"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
        ],
    )
