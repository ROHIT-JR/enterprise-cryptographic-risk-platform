"""Phase 3 enterprise identity and organization isolation.

Revision ID: 20260829_01
Revises: None
"""
from alembic import op
from sqlalchemy import inspect, text

import backend.app.models  # noqa: F401
from backend.app.models.base import Base

revision = "20260829_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    inspector = inspect(bind)
    tenant_tables = (
        "projects",
        "scans",
        "assets",
        "asset_relationships",
        "risk_findings",
        "risk_analysis",
        "migration_plan",
    )
    legacy_id = "00000000-0000-4000-8000-000000000001"
    bind.execute(
        text(
            "INSERT INTO organizations (id, name, industry, created_at, updated_at) "
            "VALUES (:id, 'Legacy Workspace', 'Unspecified', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
            "ON CONFLICT (name) DO NOTHING"
        ),
        {"id": legacy_id},
    )
    for table in tenant_tables:
        if table not in inspector.get_table_names():
            continue
        columns = {column["name"] for column in inspector.get_columns(table)}
        if "organization_id" in columns:
            continue
        op.execute(f"ALTER TABLE {table} ADD COLUMN organization_id VARCHAR(36)")
        if table == "projects":
            op.execute(
                f"UPDATE {table} SET organization_id = '{legacy_id}' "
                "WHERE organization_id IS NULL"
            )
        else:
            op.execute(
                f"UPDATE {table} child SET organization_id = project.organization_id "
                f"FROM projects project WHERE child.project_id = project.id"
            )
        op.alter_column(table, "organization_id", nullable=False)
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])


def downgrade() -> None:
    raise RuntimeError("Phase 3 tenant isolation cannot be safely downgraded")
