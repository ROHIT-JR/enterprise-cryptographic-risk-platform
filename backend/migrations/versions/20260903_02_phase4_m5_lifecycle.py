"""phase4_m5_lifecycle

Revision ID: 20260903_02_phase4_m5_lifecycle
Revises: 20260903_01_phase4_m4
Create Date: 2026-09-03 11:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260903_02_phase4_m5_lifecycle'
down_revision: str | None = '20260903_01_phase4_m4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Migration 20260829_01 bootstraps the schema via Base.metadata.create_all(),
    # which reflects whatever the *current* model classes declare — both the
    # assets columns and the crypto_lifecycle_events table below already exist
    # on a database that's never run these migrations before. Guard every
    # add_column/create_table/create_index so this migration is idempotent for
    # both a fresh database and an older one that predates this revision.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    asset_columns = {col["name"] for col in inspector.get_columns("assets")}
    asset_indexes = {idx["name"] for idx in inspector.get_indexes("assets")}

    # Asset table modifications
    if "lifecycle_state" not in asset_columns:
        op.add_column('assets', sa.Column('lifecycle_state', sa.String(length=32), nullable=True))
    if "governance_status" not in asset_columns:
        op.add_column('assets', sa.Column('governance_status', sa.String(length=32), nullable=True))
    if "lifecycle_updated_at" not in asset_columns:
        op.add_column('assets', sa.Column('lifecycle_updated_at', sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE assets SET lifecycle_state = 'DISCOVERED' WHERE lifecycle_state IS NULL")
    op.execute("UPDATE assets SET governance_status = 'ACTIVE' WHERE governance_status IS NULL")
    op.execute("UPDATE assets SET lifecycle_updated_at = CURRENT_TIMESTAMP WHERE lifecycle_updated_at IS NULL")

    # batch_alter_table: SQLite has no ALTER COLUMN — changing `nullable` has to go through
    # Alembic's recreate-the-table batch mode there. It is a plain, no-recreation ALTER COLUMN
    # on backends that support it directly, such as Postgres.
    with op.batch_alter_table("assets") as batch_op:
        batch_op.alter_column('lifecycle_state', nullable=False)
        batch_op.alter_column('governance_status', nullable=False)
        batch_op.alter_column('lifecycle_updated_at', nullable=False)

    if op.f('ix_assets_lifecycle_state') not in asset_indexes:
        op.create_index(op.f('ix_assets_lifecycle_state'), 'assets', ['lifecycle_state'], unique=False)
    if op.f('ix_assets_governance_status') not in asset_indexes:
        op.create_index(op.f('ix_assets_governance_status'), 'assets', ['governance_status'], unique=False)

    if inspector.has_table('crypto_lifecycle_events'):
        return

    # CryptoLifecycleEvent table creation
    op.create_table('crypto_lifecycle_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('asset_id', sa.String(length=36), nullable=False),
        sa.Column('previous_state', sa.String(length=32), nullable=True),
        sa.Column('new_state', sa.String(length=32), nullable=False),
        sa.Column('previous_governance_status', sa.String(length=32), nullable=True),
        sa.Column('new_governance_status', sa.String(length=32), nullable=False),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('reason', sa.String(length=1024), nullable=True),
        sa.Column('actor_user_id', sa.String(length=36), nullable=True),
        sa.Column('actor_role', sa.String(length=32), nullable=True),
        sa.Column('related_risk_analysis_id', sa.String(length=36), nullable=True),
        sa.Column('related_plan_id', sa.String(length=36), nullable=True),
        sa.Column('migration_wave', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('engine_version', sa.String(length=32), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crypto_lifecycle_events_asset_id'), 'crypto_lifecycle_events', ['asset_id'], unique=False)
    op.create_index(op.f('ix_crypto_lifecycle_events_organization_id'), 'crypto_lifecycle_events', ['organization_id'], unique=False)
    op.create_index(op.f('ix_crypto_lifecycle_events_project_id'), 'crypto_lifecycle_events', ['project_id'], unique=False)
    op.create_index(op.f('ix_crypto_lifecycle_events_new_state'), 'crypto_lifecycle_events', ['new_state'], unique=False)
    op.create_index(op.f('ix_crypto_lifecycle_events_previous_state'), 'crypto_lifecycle_events', ['previous_state'], unique=False)
    op.create_index(op.f('ix_crypto_lifecycle_events_new_governance_status'), 'crypto_lifecycle_events', ['new_governance_status'], unique=False)
    op.create_index(op.f('ix_crypto_lifecycle_events_previous_governance_status'), 'crypto_lifecycle_events', ['previous_governance_status'], unique=False)
    op.create_index(op.f('ix_crypto_lifecycle_events_migration_wave'), 'crypto_lifecycle_events', ['migration_wave'], unique=False)
    op.create_index(op.f('ix_crypto_lifecycle_events_related_plan_id'), 'crypto_lifecycle_events', ['related_plan_id'], unique=False)
    op.create_index(op.f('ix_crypto_lifecycle_events_related_risk_analysis_id'), 'crypto_lifecycle_events', ['related_risk_analysis_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_crypto_lifecycle_events_related_risk_analysis_id'), table_name='crypto_lifecycle_events')
    op.drop_index(op.f('ix_crypto_lifecycle_events_related_plan_id'), table_name='crypto_lifecycle_events')
    op.drop_index(op.f('ix_crypto_lifecycle_events_migration_wave'), table_name='crypto_lifecycle_events')
    op.drop_index(op.f('ix_crypto_lifecycle_events_previous_governance_status'), table_name='crypto_lifecycle_events')
    op.drop_index(op.f('ix_crypto_lifecycle_events_new_governance_status'), table_name='crypto_lifecycle_events')
    op.drop_index(op.f('ix_crypto_lifecycle_events_previous_state'), table_name='crypto_lifecycle_events')
    op.drop_index(op.f('ix_crypto_lifecycle_events_new_state'), table_name='crypto_lifecycle_events')
    op.drop_index(op.f('ix_crypto_lifecycle_events_project_id'), table_name='crypto_lifecycle_events')
    op.drop_index(op.f('ix_crypto_lifecycle_events_organization_id'), table_name='crypto_lifecycle_events')
    op.drop_index(op.f('ix_crypto_lifecycle_events_asset_id'), table_name='crypto_lifecycle_events')
    op.drop_table('crypto_lifecycle_events')
    
    op.drop_index(op.f('ix_assets_governance_status'), table_name='assets')
    op.drop_index(op.f('ix_assets_lifecycle_state'), table_name='assets')
    op.drop_column('assets', 'lifecycle_updated_at')
    op.drop_column('assets', 'governance_status')
    op.drop_column('assets', 'lifecycle_state')
