"""Align platform token cache storage with the extension TEXT model.

Existing values and expiry metadata are retained. Downgrade refuses long values
rather than truncating credentials; operators must resolve them before retrying.
"""

import sqlalchemy as sa

from alembic import op

revision = "c9d27f06a318"
down_revision = "a68c19e2f407"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "sys_platform_token",
        "token",
        existing_type=sa.String(255),
        type_=sa.Text(),
        existing_nullable=False,
        postgresql_using="token::text",
    )


def downgrade():
    bind = op.get_bind()
    # Hold the lock through the check and type change to exclude concurrent writes.
    bind.execute(sa.text("LOCK TABLE sys_platform_token IN ACCESS EXCLUSIVE MODE"))
    if bind.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM sys_platform_token WHERE char_length(token) > 255)"
        )
    ).scalar():
        raise RuntimeError(
            "Cannot downgrade platform token storage: values exceed 255 characters"
        )
    op.alter_column(
        "sys_platform_token",
        "token",
        existing_type=sa.Text(),
        type_=sa.String(255),
        existing_nullable=False,
        postgresql_using="token::varchar(255)",
    )
