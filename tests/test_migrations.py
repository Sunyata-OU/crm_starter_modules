"""The two modules that ship their own migrations, run through ``crm migrate``.

These need a checkout of ``crm_starter`` (its ``migrations/`` and ``alembic.ini``
are not part of the installed package), which is how CI installs it. The tests
run the real command in a subprocess so nothing is faked: the module's revisions
have to chain onto the framework's and apply.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
import sqlalchemy as sa

cli = pytest.importorskip("app.cli")
ROOT = cli.ROOT

pytestmark = pytest.mark.skipif(
    not (ROOT / "alembic.ini").exists(),
    reason="needs a crm_starter checkout (migrations are not packaged)",
)

MODULES = "helpdesk,keycloak_accounts"


def run(db, *args, modules=MODULES):
    env = {
        **os.environ,
        "CRM_DATABASE_URL": f"sqlite+aiosqlite:///{db}",
        "CRM_MODULES": modules,
    }
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120,
    )


def tables(db) -> set[str]:
    return set(sa.inspect(sa.create_engine(f"sqlite:///{db}")).get_table_names())


def test_a_fresh_database_gets_the_framework_and_both_modules(tmp_path):
    db = tmp_path / "fresh.db"
    result = run(db, "migrate")
    assert result.returncode == 0, result.stdout + result.stderr
    assert {"tasks", "tickets", "ticket_messages", "impersonation_log"} <= tables(db)


def test_a_database_that_already_has_the_tables_migrates_cleanly(tmp_path):
    """These features began inside the framework, so a database may have
    their tables with no record of the modules' revisions."""
    db = tmp_path / "existing.db"
    assert run(db, "migrate").returncode == 0
    with sa.create_engine(f"sqlite:///{db}").begin() as conn:
        conn.execute(sa.text("DELETE FROM alembic_version"))
        # As if only the framework's own history had been applied.
        conn.execute(sa.text("INSERT INTO alembic_version VALUES ('7d2e91b4a6c0')"))
    result = run(db, "migrate")
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_module_alone_is_enough(tmp_path):
    db = tmp_path / "one.db"
    result = run(db, "migrate", modules="helpdesk")
    assert result.returncode == 0, result.stdout + result.stderr
    found = tables(db)
    assert "tickets" in found and "impersonation_log" not in found


def test_the_declared_tables_match_the_migrations(tmp_path):
    """No drift: what autogenerate would add or change is nothing."""

    db = tmp_path / "drift.db"
    assert run(db, "migrate").returncode == 0
    code = (
        "import sqlalchemy as sa;"
        "from alembic.migration import MigrationContext;"
        "from alembic.autogenerate import compare_metadata;"
        "from app.core.modules import select;"
        "from app.schema import metadata;"
        f"select(enabled='{MODULES}'.split(','));"
        f"c=sa.create_engine('sqlite:///{db}').connect();"
        "ctx=MigrationContext.configure(c, opts={'compare_type': True});"
        "print([d for d in compare_metadata(ctx, metadata) "
        "if any(t in str(d) for t in ('tickets','ticket_messages','impersonation_log'))])"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "[]", out.stdout


def test_the_sweep_command_is_added(tmp_path):
    result = run(tmp_path / "x.db", "--help")
    assert "helpdesk-sweep" in result.stdout, result.stdout
