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

    @field_validator("watchers", mode="before")
    @classmethod
    def _split_csv(cls, value):
        """Accept a comma-separated string, since env vars cannot hold lists."""
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> HelpdeskSettings:
    return HelpdeskSettings()
