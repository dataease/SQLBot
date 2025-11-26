"""empty message

Revision ID: e408f8766753
Revises: cb12c4238120
Create Date: 2025-11-24 17:34:04.436927

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e408f8766753'
down_revision = 'cb12c4238120'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('ds_recommended_problem',
                    sa.Column('id', sa.BIGINT(),
                              sa.Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=9999999999,
                                          cycle=False, cache=1), autoincrement=True, nullable=False),
                    sa.Column('datasource_id', sa.BIGINT(), autoincrement=False, nullable=True),
                    sa.Column('question', sa.TEXT(), autoincrement=False, nullable=True),
                    sa.Column('remark', sa.TEXT(), autoincrement=False, nullable=True),
                    sa.Column('sort', sa.BIGINT(), autoincrement=False, nullable=True),
                    sa.Column('create_time', postgresql.TIMESTAMP(precision=6), autoincrement=False, nullable=True),
                    sa.Column('create_by', sa.BIGINT(), autoincrement=False, nullable=True),
                    sa.PrimaryKeyConstraint('id', name=op.f('ds_recommended_problem_pkey'))
                    )
    op.add_column('core_datasource', sa.Column('recommended_config', sa.BigInteger(),default=0, nullable=True))

def downgrade():
    op.drop_table('ds_recommended_problem')
    op.drop_column('core_datasource', 'recommended_config')

