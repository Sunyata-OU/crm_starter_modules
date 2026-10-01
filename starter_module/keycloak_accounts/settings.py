"""Configuration for ``keycloak_accounts``, read from ``CRM_KEYCLOAK_*`` or ``.env``.

The module reads its own settings rather than adding fields to the framework's
``Settings``, so installing it changes nothing about the framework.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class KeycloakSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="CRM_KEYCLOAK_"
    )

    #: Keycloak's base URL, e.g. ``https://auth.example.com``. Needed to send
    #: the browser to the impersonation endpoint.
    url: str = ""
    realm: str = "master"
    #: The ``connections.yaml`` REST connection carrying admin credentials for
    #: the realm, which the accounts list is read through.
    connection: str = "api.keycloak"
    #: The roles whose holders are "the staff": listed on the accounts screen
    #: and offered to ``@mention``. Each must exist -- Keycloak answers 404 for
    #: a role it does not have, which would take the screen down.
    roles: Annotated[list[str], NoDecode] = ["admin"]
    #: The clientId those roles are defined on, when they are *client* roles
    #: rather than realm roles. Empty reads the realm-role endpoint.
    client: str = ""
    #: That client's internal uuid, to skip the lookup of it at startup.
    client_uuid: str = ""
    #: Where to land after impersonating -- the application the impersonated
    #: session is for. Empty lands on Keycloak's own account page.
    frontend_url: str = ""

    @field_validator("roles", mode="before")
    @classmethod
    def _split_csv(cls, value):
        """Accept a comma-separated string, since env vars cannot hold lists."""
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> KeycloakSettings:
    return KeycloakSettings()
