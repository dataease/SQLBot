"""empty message

Revision ID: 3d4bd2d673dc
Revises: 24e961f6326b
Create Date: 2025-12-19 13:30:54.743171

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3d4bd2d673dc'
down_revision = '24e961f6326b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('sys_logs',
                    sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
                    sa.Column('operation_type', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
                    sa.Column('operation_detail', sa.TEXT(), autoincrement=False, nullable=True),
                    sa.Column('user_id', sa.BIGINT(), autoincrement=False, nullable=True),
                    sa.Column('operation_status', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
                    sa.Column('oid', sa.BIGINT(), autoincrement=False, nullable=True),
                    sa.Column('ip_address', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
                    sa.Column('user_agent', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
                    sa.Column('execution_time', sa.BIGINT(), autoincrement=False, nullable=True),
                    sa.Column('error_message', sa.TEXT(), autoincrement=False, nullable=True),
                    sa.Column('create_time', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                    sa.Column('module', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
                    sa.Column('remark', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
                    sa.Column('resource_id',sa.TEXT(), autoincrement=False, nullable=True),
                    sa.Column('request_method', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
                    sa.Column('request_path', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
                    sa.PrimaryKeyConstraint('id', name=op.f('sys_logs_pkey'))
                    )


def downgrade():
    op.drop_table('sys_logs')
