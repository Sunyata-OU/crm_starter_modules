"""Helpers for tests that drive the real application.

The framework's own suite has fuller versions of these; a module only needs
enough to sign someone in and submit a form.
"""

from __future__ import annotations

import re

from app.core.registry import Registry
from starlette.testclient import TestClient


def build_registry() -> Registry:
    """An empty registry: a module's tests add the resources they exercise."""
    return Registry()


def sign_in(
    client: TestClient, *, email: str, roles: list[str], subject: str = "", timezone: str = "UTC"
) -> None:
    """Put a signed session cookie in place, bypassing the login form."""
    from app.core.results import Identity
    from starlette.responses import Response

    state = client.app.state.crm
    identity = Identity(
        subject=subject or email,
        email=email,
        display_name=email.split("@")[0].title(),
        roles=frozenset(roles),
        provider="session",
        timezone=timezone,
    )
    carrier = Response()
    state.sessions.save_identity(carrier, identity)
    cookie = carrier.headers["set-cookie"].split(";")[0]
    name, _, value = cookie.partition("=")
    client.cookies.set(name, value)


def csrf_from(client: TestClient, url: str) -> str:
    """Pull a CSRF token out of a rendered form."""
    html = client.get(url).text
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, f"no CSRF token found in {url}"
    return match.group(1)
