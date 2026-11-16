"""076_agent_token_ddl

Bearer tokens for the SQLBot MCP server used by external agents. Only a
SHA-256 digest of each token is stored.

Revision ID: 3b7e0c1f9a42
Revises: d91543ca7b21
Create Date: 2026-11-13 18:00:00

"""
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

from alembic import op

# revision identifiers, used by Alembic.
revision = '3b7e0c1f9a42'
down_revision = 'd91543ca7b21'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sys_agent_token',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('uid', sa.BigInteger(), nullable=False),
        sa.Column('oid', sa.BigInteger(), nullable=False),
        sa.Column('token_prefix', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('status', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('allowed_ds_ids', sa.Text(), nullable=True),
        sa.Column('create_time', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('last_used_time', sa.BigInteger(), nullable=True),
        sa.Column('last_used_ip', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sys_agent_token_id'), 'sys_agent_token', ['id'], unique=False)
    op.create_index(op.f('ix_sys_agent_token_uid'), 'sys_agent_token', ['uid'], unique=False)
    op.create_index(op.f('ix_sys_agent_token_token_prefix'), 'sys_agent_token', ['token_prefix'], unique=True)


def downgrade():
    # Dropping the table revokes every issued agent token.
    op.drop_index(op.f('ix_sys_agent_token_token_prefix'), table_name='sys_agent_token')
    op.drop_index(op.f('ix_sys_agent_token_uid'), table_name='sys_agent_token')
    op.drop_index(op.f('ix_sys_agent_token_id'), table_name='sys_agent_token')
    op.drop_table('sys_agent_token')
