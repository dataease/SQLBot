"""add table_select_answer column to chat_record

Revision ID: 054_table_select
Revises: 5755c0b95839
Create Date: 2025-12-23

"""
from alembic import op
import sqlalchemy as sa

revision = '054_table_select'
down_revision = '5755c0b95839'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chat_record', sa.Column('table_select_answer', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('chat_record', 'table_select_answer')
