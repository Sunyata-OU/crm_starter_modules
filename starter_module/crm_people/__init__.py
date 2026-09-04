"""Company People / Contacts module declaration."""

from __future__ import annotations

from app.core.registry import Registry
from app.fields.types import (
    BooleanField,
    DateTimeField,
    EmailField,
    PhoneField,
    RelationField,
    StatusField,
    TextAreaField,
    TextField,
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
    "name": "crm_people",
    "label": "People & Contacts",
    "description": "Individual contacts associated with companies.",
    "depends": ("core_identity",),
    "menu_groups": {"Records": 10},
    "optional": True,
}

STATUSES = [
    ("lead", "Lead", "amber"),
    ("active", "Active", "green"),
    ("dormant", "Dormant", "default"),
    ("churned", "Churned", "red"),
]


def register(registry: Registry) -> None:
    registry.add_resource(_people())


def _people() -> Resource:
    return Resource(
        "people",
        provider="db.main#company_people",
        label="Person",
        label_plural="People",
        icon="🗎",
        menu_group="Records",
        menu_order=20,
        display_field="name",
        default_sort=["name"],
        timeline=True,
        policy=DbPolicy(owner_field="owner", identity_attr="email"),
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("name", label="Full Name", required=True, searchable=True, inline_editable=True),
            EmailField("email", label="Email", required=True, searchable=True, inline_editable=True),
            PhoneField("phone", label="Phone", searchable=True, inline_editable=True),
            TextField("title", label="Job Title", searchable=True, inline_editable=True),
            RelationField("company_id", label="Company", resource="companies", display="name", in_filter=True),
            StatusField("status", choices=STATUSES, default="active", in_filter=True, inline_editable=True),
            BooleanField("is_primary", label="Primary Contact", default=False, inline_editable=True),
            TextField("owner", label="Owner", in_filter=True, inline_editable=True),
            DateTimeField("last_contacted", label="Last Contacted", readonly=True, in_form=False),
            TextAreaField("notes", label="Notes", rows=3),
        ],
        search=SearchSpec(
            fields=("name", "email", "phone", "title", "notes"),
            filters=("status", "company_id", "owner", "is_primary"),
        ),
        views=[
            ListView(
                columns=[
                    Column("name", link=True, width="25%"),
                    "email",
                    "title",
                    "company_id",
                    "status",
                    "owner",
                ],
                default_sort=["name"],
            ),
            FormView(
                sections=[
                    Section("Personal Info", fields=["name", "email", "phone", "title", "is_primary"]),
                    Section("Company & Owner", fields=["company_id", "status", "owner"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
            DetailView(
                sections=[
                    Section("Contact Information", fields=["name", "email", "phone", "title", "status", "is_primary"]),
                    Section("Affiliation & Owner", fields=["company_id", "owner", "last_contacted"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
        ],
    )
