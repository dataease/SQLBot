from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '547df942eb90'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('data_training', sa.Column('embedded', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    op.add_column('terminology', sa.Column('embedded', sa.Boolean(), nullable=True, server_default=sa.text('false')))


def downgrade():
    op.drop_column('data_training', 'embedded')
    op.drop_column('terminology', 'embedded')
