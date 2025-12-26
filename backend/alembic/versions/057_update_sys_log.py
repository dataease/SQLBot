"""empty message

Revision ID: c431a0bf478b
Revises: d9a5589fc00b
Create Date: 2025-12-25 12:50:59.790439

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c431a0bf478b'
down_revision = 'd9a5589fc00b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sys_logs', sa.Column('user_name', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('sys_logs', sa.Column('resource_name', sa.TEXT(), autoincrement=False, nullable=True))

def downgrade():
    op.drop_column('sys_logs', 'user_name')
    op.drop_column('sys_logs', 'resource_name')

