"""CRM Activities & Timeline Log Module."""

from __future__ import annotations

from app.core.registry import Registry
from app.fields.types import (
    DateTimeField,
    RelationField,
    SelectField,
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
    "name": "crm_activities",
    "label": "Activities & Notes",
    "description": "Log calls, meetings, emails, and notes across records.",
    "depends": ("core_identity",),
    "menu_groups": {"Records": 10},
    "optional": True,
}

KINDS = [
    ("call", "Call"),
    ("meeting", "Meeting"),
    ("email", "Email"),
    ("note", "Note"),
]


def register(registry: Registry) -> None:
    registry.add_resource(_activities())


def _activities() -> Resource:
    return Resource(
        "crm_activities",
        provider="db.main#crm_activities",
        label="Activity",
        label_plural="Activities",
        icon="💬",
        menu_group="Records",
        menu_order=30,
        display_field="subject",
        default_sort=["-id"],
        timeline=True,
        policy=DbPolicy(owner_field="owner", identity_attr="email"),
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("subject", label="Subject", required=True, searchable=True, inline_editable=True),
            SelectField("kind", choices=KINDS, default="call", in_filter=True, inline_editable=True),
            RelationField("company_id", label="Company", resource="companies", display="name", in_filter=True),
            RelationField("person_id", label="Person", resource="people", display="name", in_filter=True),
            RelationField("deal_id", label="Deal", resource="sales_deals", display="name", in_filter=True),
            TextField("owner", label="Logged By", in_filter=True, inline_editable=True),
            TextAreaField("notes", label="Notes & Summary", rows=4),
        ],
        search=SearchSpec(
            fields=("subject", "notes"),
            filters=("kind", "company_id", "person_id", "deal_id", "owner"),
        ),
        views=[
            ListView(
                columns=[
                    Column("subject", link=True, width="30%"),
                    "kind",
                    "company_id",
                    "person_id",
                    "deal_id",
                    "owner",
                ],
                default_sort=["-id"],
            ),
            FormView(
                sections=[
                    Section("Activity Info", fields=["subject", "kind"]),
                    Section("Linked Entities", fields=["company_id", "person_id", "deal_id", "owner"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
            DetailView(
                sections=[
                    Section("Overview", fields=["subject", "kind", "owner"]),
                    Section("Links", fields=["company_id", "person_id", "deal_id"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
        ],
    )
