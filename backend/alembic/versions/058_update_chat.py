"""empty message

Revision ID: fb2e8dd19158
Revises: c431a0bf478b
Create Date: 2025-12-29 17:18:49.072320

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

# revision identifiers, used by Alembic.
revision = 'fb2e8dd19158'
down_revision = 'c431a0bf478b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chat', sa.Column('recommended_question_answer', sa.TEXT(), nullable=True))
    op.add_column('chat', sa.Column('recommended_question', sa.TEXT(), nullable=True))
    op.add_column('chat', sa.Column('recommended_generate', sa.Boolean(),  nullable=True))
    # ### end Alembic commands ###


def downgrade():
    op.drop_column('chat', 'recommended_question_answer')
    op.drop_column('chat', 'recommended_question')
    op.drop_column('chat', 'recommended_generate')
    # ### end Alembic commands ###
