"""Account-linking storage shared with the authentication extension.

Duplicate historical mappings must be reconciled explicitly, never auto-merged.
Downgrade drops pending requests and display metadata, retaining identity links.
"""

import sqlalchemy as sa

from alembic import op

revision = "a68c19e2f407"
down_revision = "d91543ca7b21"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    for columns in ("origin, platform_uid", "uid, origin"):
        duplicate = bind.execute(
            sa.text(
                f"SELECT 1 FROM sys_user_platform GROUP BY {columns} HAVING count(*) > 1 LIMIT 1"
            )
        ).first()
        if duplicate:
            raise RuntimeError("Duplicate account mappings: reconcile before upgrading")
    op.add_column(
        "sys_user_platform",
        sa.Column(
            "config_fingerprint", sa.String(64), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "sys_user_platform",
        sa.Column("display_name", sa.String(255), nullable=False, server_default=""),
    )
    op.create_unique_constraint(
        "uq_user_platform_identity", "sys_user_platform", ["origin", "platform_uid"]
    )
    op.create_unique_constraint(
        "uq_user_platform_owner", "sys_user_platform", ["uid", "origin"]
    )
    op.create_table(
        "sys_user_binding_request",
        sa.Column("state", sa.String(96), primary_key=True),
        sa.Column("uid", sa.BigInteger(), nullable=False),
        sa.Column("origin", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("credential_fingerprint", sa.String(64), nullable=False),
        sa.Column("config_fingerprint", sa.String(64), nullable=False),
        sa.Column("callback_url", sa.String(2048), nullable=False),
        sa.Column("platform_uid", sa.String(255), nullable=False, server_default=""),
        sa.Column("display_name", sa.String(255), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_sys_user_binding_request_uid", "sys_user_binding_request", ["uid"]
    )
    op.create_index(
        "ix_sys_user_binding_request_created_at",
        "sys_user_binding_request",
        ["created_at"],
    )

    op.create_index(
        "ix_sys_user_binding_request_expires_at",
        "sys_user_binding_request",
        ["expires_at"],
    )


def downgrade():
    op.drop_table("sys_user_binding_request")
    op.drop_constraint("uq_user_platform_owner", "sys_user_platform", type_="unique")
    op.drop_constraint("uq_user_platform_identity", "sys_user_platform", type_="unique")
    op.drop_column("sys_user_platform", "display_name")
    op.drop_column("sys_user_platform", "config_fingerprint")
