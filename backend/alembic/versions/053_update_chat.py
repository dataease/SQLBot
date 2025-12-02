"""empty message

Revision ID: 5755c0b95839
Revises: e408f8766753
Create Date: 2025-12-02 13:46:06.905576

"""
from alembic import op
import sqlalchemy as sa

revision = '5755c0b95839'
down_revision = 'e408f8766753'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chat', sa.Column('brief_generate', sa.Boolean(), nullable=True))
    op.execute("UPDATE chat SET brief_generate = true WHERE brief_generate IS NULL")
    with op.batch_alter_table('chat') as batch_op:
        batch_op.alter_column('brief_generate',
                             server_default=sa.text('false'),
                             nullable=False)
    # ### end Alembic commands ###


def downgrade():
    op.drop_column('chat', 'brief_generate')
    # ### end Alembic commands ###