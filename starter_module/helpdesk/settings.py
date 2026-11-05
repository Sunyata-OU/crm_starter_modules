"""Configuration for the helpdesk, read from ``CRM_HELPDESK_*`` or ``.env``.

The module reads its own settings rather than adding fields to the framework's
``Settings``, so installing it changes nothing about the framework.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class HelpdeskSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="CRM_HELPDESK_"
    )

    #: Who hears about a new ticket nobody is on, and one ageing past
    #: `stale_hours` while assigned. Same reasoning as `CRM_TASK_WATCHERS`:
    #: naming nobody means the sweep says nothing about either, which is honest
    #: where guessing an owner would not be.
    watchers: Annotated[list[str], NoDecode] = []
    #: How long an open ticket may sit without a fresh sweep notification
    #: before the sweep decides it is worth mentioning again. Longer than
    #: `DUE_WINDOW` in `app.tasks` because a ticket has no due date of its own
    #: to be more or less urgent about -- this is purely "has it been quiet
    #: for a worryingly long time".
    stale_hours: float = 48.0
    #: Domain used in the Message-ID this application generates for outbound
    #: replies. Cosmetic -- nothing dials it -- but a Message-ID's domain half
    #: is conventionally the sending system's, and `localhost` in a header a
    #: customer's mail client stores forever looks like a misconfiguration
    #: even when delivery worked perfectly.
    mail_domain: str = "localhost"

    #: The support mailbox `crm helpdesk-ingest` reads, over IMAP. Read-only: it
    #: opens the folder read-only and never marks anything seen. An empty host
    #: means no mailbox is configured, and the command says so rather than guess.
    imap_host: str = ""
    imap_port: int = 993
    imap_username: str = ""
    imap_password: str = ""
    imap_ssl: bool = True
    imap_folder: str = "INBOX"
    #: How far back each run looks. Messages already filed are skipped by
    #: Message-ID, so this only needs to cover the longest the job could be down.
    ingest_days: int = 7
    #: At most this many new messages are filed per run; the rest wait for the
    #: next one, so a backlog cannot make one run hold the database for ever.
    ingest_limit: int = 100
    #: Senders never filed, besides the framework's `CRM_SMTP_SENDER`: our own
    #: addresses, a relay that copies us in.
    ignore_senders: Annotated[list[str], NoDecode] = []

    @field_validator("watchers", "ignore_senders", mode="before")
    @classmethod
    def _split_csv(cls, value):
        """Accept a comma-separated string, since env vars cannot hold lists."""
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> HelpdeskSettings:
    return HelpdeskSettings()
