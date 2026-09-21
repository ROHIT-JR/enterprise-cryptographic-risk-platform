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
    url = f"sqlite+pysqlite:///{tmp_path / 'migrated.db'}"
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
