"""Document Attachments Module."""

from __future__ import annotations

from app.core.registry import Registry
from app.fields.types import (
    FileField,
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
    "name": "documents_attachments",
    "label": "Documents & Attachments",
    "description": "Store and manage file uploads, proposals, contracts, and attachments.",
    "depends": ("core_identity",),
    "menu_groups": {"Workspace": 5},
    "optional": True,
}

CATEGORIES = [
    ("contract", "Contract"),
    ("proposal", "Proposal"),
    ("invoice", "Invoice"),
    ("nda", "NDA"),
    ("other", "Other"),
]


def register(registry: Registry) -> None:
    registry.add_resource(_documents())


def _documents() -> Resource:
    return Resource(
        "documents_attachments",
        provider="db.main#documents",
        label="Document",
        label_plural="Documents",
        icon="📁",
        menu_group="Workspace",
        menu_order=20,
        display_field="title",
        default_sort=["-id"],
        timeline=True,
        policy=DbPolicy(owner_field="owner", identity_attr="email"),
        fields=[
            TextField("id", label="ID", in_form=False, in_detail=False, in_list=False),
            TextField("title", label="Document Title", required=True, searchable=True, inline_editable=True),
            SelectField("category", choices=CATEGORIES, default="contract", in_filter=True, inline_editable=True),
            FileField("file_path", label="Attachment File"),
            RelationField("company_id", label="Company", resource="companies", display="name", in_filter=True),
            RelationField("deal_id", label="Deal", resource="sales_deals", display="name", in_filter=True),
            TextField("owner", label="Uploaded By", in_filter=True, inline_editable=True),
            TextAreaField("notes", label="Notes", rows=3),
        ],
        search=SearchSpec(
            fields=("title", "notes"),
            filters=("category", "company_id", "deal_id", "owner"),
        ),
        views=[
            ListView(
                columns=[
                    Column("title", link=True, width="30%"),
                    "category",
                    "company_id",
                    "deal_id",
                    "owner",
                ],
                default_sort=["-id"],
            ),
            FormView(
                sections=[
                    Section("Document Metadata", fields=["title", "category", "file_path"]),
                    Section("Links & Owner", fields=["company_id", "deal_id", "owner"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
            DetailView(
                sections=[
                    Section("Overview", fields=["title", "category", "file_path", "owner"]),
                    Section("Links", fields=["company_id", "deal_id"]),
                    Section("Notes", fields=["notes"]),
                ]
            ),
        ],
    )
