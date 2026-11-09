"""Create internal complete metadata embeddings without running model inference."""

import sqlalchemy as sa

from alembic import op

revision = "ed42b7f169a3"
down_revision = "c71e75fd6a30"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "metadata_embedding",
        sa.Column("resource_type", sa.String(32), primary_key=True),
        sa.Column("resource_id", sa.BigInteger(), primary_key=True),
        sa.Column("format_version", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("vectors_hash", sa.String(64), nullable=False),
        sa.Column("vectors", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("metadata_embedding")
