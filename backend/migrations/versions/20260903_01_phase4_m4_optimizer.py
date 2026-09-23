"""Add M4 optimizer fields to migration_plan

Revision ID: 20260903_01_phase4_m4
Revises: 20260829_01_phase3_enterprise
Create Date: 2026-09-03 10:11:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260903_01_phase4_m4'
down_revision = '20260829_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # On a fresh database revision 20260829_01 already builds the *current* schema, so these
    # columns exist. Only databases created before this revision are missing them.
    # batch_alter_table: SQLite has no ALTER COLUMN, so toggling `nullable` (or altering a
    # column right after adding it) has to go through Alembic's recreate-the-table batch mode.
    # It is a no-op wrapper on backends that support ALTER COLUMN directly, such as Postgres.
    columns = {c["name"]: c for c in sa.inspect(op.get_bind()).get_columns("migration_plan")}
    with op.batch_alter_table("migration_plan") as batch_op:
        if "priority_score" not in columns:
            batch_op.add_column(sa.Column('priority_score', sa.Float(), nullable=True))
        if "confidence" not in columns:
            batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=True))
        if "optimizer_version" not in columns:
            batch_op.add_column(
                sa.Column('optimizer_version', sa.String(length=32), nullable=True)
            )
        if "constraints" not in columns:
            batch_op.add_column(sa.Column('constraints', sa.JSON(), nullable=True))
        if not columns["wave"]["nullable"]:
            batch_op.alter_column('wave', existing_type=sa.Integer(), nullable=True)
    if "constraints" not in columns:
        # Backfill constraints as empty lists; needs the column to exist first, so it runs
        # outside the batch (SQLite rebuilds the table mid-batch and empties the old rows' view).
        op.execute("UPDATE migration_plan SET constraints = '[]' WHERE constraints IS NULL")
        with op.batch_alter_table("migration_plan") as batch_op:
            batch_op.alter_column('constraints', existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("migration_plan") as batch_op:
        batch_op.alter_column('wave', existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column('constraints')
        batch_op.drop_column('optimizer_version')
        batch_op.drop_column('confidence')
        batch_op.drop_column('priority_score')
