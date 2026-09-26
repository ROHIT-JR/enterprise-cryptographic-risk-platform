"""Add is_platform_admin flag to users

Revision ID: 20260926_01_platform_admin
Revises: 20260903_02_phase4_m5_lifecycle
Create Date: 2026-09-26 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "20260926_01_platform_admin"
down_revision = "20260903_02_phase4_m5_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {col["name"] for col in sa.inspect(bind).get_columns("users")}
    if "is_platform_admin" not in existing_columns:
        op.add_column(
            "users",
            sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    op.drop_column("users", "is_platform_admin")
