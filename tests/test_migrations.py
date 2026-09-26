"""The Alembic chain must resolve and must build a working database from nothing.

The production Compose file runs `alembic upgrade head` before starting the API, so a broken
chain (or a revision that re-adds something an earlier revision already created) stops the whole
stack from booting.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

import backend.app.models  # noqa: F401  (registers every table)
from backend.app.models.base import Base

ROOT = Path(__file__).resolve().parent.parent


def _alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "ECDAT_DATABASE_URL": database_url,
        "ECDAT_NEO4J_ENABLED": "false",
    }
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_revision_chain_resolves_to_a_single_head():
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    scripts.get_revisions("heads")  # raises KeyError if a down_revision points at nothing
    revisions = list(scripts.walk_revisions())
    assert len(scripts.get_heads()) == 1, "migrations have forked; merge the branches"
    # every revision except the base has a parent that exists
    known = {revision.revision for revision in revisions}
    for revision in revisions:
        parent = revision.down_revision  # None, one id, or a tuple for merge revisions
        parents = () if parent is None else (parent,) if isinstance(parent, str) else tuple(parent)
        for name in parents:
            assert name in known, f"{revision.revision} points at unknown parent {name!r}"


@pytest.fixture
def migrated(tmp_path):
    # ECDAT_TEST_MIGRATIONS_URL lets CI point every test in this module at a real Postgres
    # service container instead of a throwaway SQLite file, so the same assertions run against
    # the engine the production Compose stack actually uses. All tests in this module share that
    # one database when it is set (Postgres tests run sequentially, not with pytest-xdist), and
    # each test that touches it leaves it at `head` again before returning.
    default_url = f"sqlite+pysqlite:///{tmp_path / 'migrated.db'}"
    url = os.environ.get("ECDAT_TEST_MIGRATIONS_URL") or default_url
    result = _alembic(url, "upgrade", "head")
    assert result.returncode == 0, result.stderr[-2000:]
    return url


def test_upgrade_head_builds_every_model_table_on_an_empty_database(migrated):
    engine = create_engine(migrated)
    tables = set(inspect(engine).get_table_names())
    assert tables == {*Base.metadata.tables, "alembic_version"}

    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    with engine.connect() as connection:
        stamped = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert stamped == scripts.get_current_head()


def test_migrated_columns_match_the_models(migrated):
    inspector = inspect(create_engine(migrated))
    for name, table in Base.metadata.tables.items():
        actual = {column["name"] for column in inspector.get_columns(name)}
        assert actual == {column.name for column in table.columns}, name


def test_upgrading_twice_is_a_no_op(migrated):
    again = _alembic(migrated, "upgrade", "head")
    assert again.returncode == 0, again.stderr[-2000:]
    assert _alembic(migrated, "current").returncode == 0


def test_upgrade_head_adds_the_phase4_columns_to_a_database_that_predates_them(migrated):
    """On a genuinely fresh database, revision 20260829_01's `create_all` already builds every
    column, so the phase4 migrations' `if column not in columns: add it` guards never run on any
    of the tests above — every one of them upgrades a database that never lacked the columns.

    Downgrading to the base revision runs the real, unguarded `downgrade()` functions and drops
    those columns and the `crypto_lifecycle_events` table, producing exactly the schema the
    guards describe: "databases created before this revision". Upgrading again is the first time
    any test exercises the add-column branches themselves, on SQLite and (in CI) on Postgres.

    This does not exercise the `constraints`/lifecycle backfill UPDATE statements against
    pre-existing rows with NULL values: reaching that state would need a row that predates the
    column, which a downgrade (drops the column, destroying its data) cannot simulate. The
    guard's existence check — the thing that previously crashed with "column already exists" —
    is what this test covers.
    """
    result = _alembic(migrated, "downgrade", "20260829_01")
    assert result.returncode == 0, result.stderr[-2000:]
    engine = create_engine(migrated)
    inspector = inspect(engine)
    assert "priority_score" not in {c["name"] for c in inspector.get_columns("migration_plan")}
    assert "crypto_lifecycle_events" not in inspector.get_table_names()

    result = _alembic(migrated, "upgrade", "head")
    assert result.returncode == 0, result.stderr[-2000:]

    inspector = inspect(create_engine(migrated))
    for name, table in Base.metadata.tables.items():
        actual = {column["name"] for column in inspector.get_columns(name)}
        assert actual == {column.name for column in table.columns}, name
    with engine.connect() as connection:
        stamped = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert stamped == scripts.get_current_head()
