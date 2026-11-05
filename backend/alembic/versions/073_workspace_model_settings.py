"""Add workspace model policy; existing and new workspaces keep system defaults."""

import sqlalchemy as sa
from alembic import op

revision = "c71e75fd6a30"
down_revision = "f898322341a5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sys_workspace", sa.Column("enable_custom_model", sa.Boolean(), server_default=sa.false(), nullable=False, comment="是否指定工作空间模型"))
    op.add_column("sys_workspace", sa.Column("custom_model", sa.String(255), nullable=True, comment="工作空间默认模型 ID；显式留空禁止模型调用"))


def downgrade():
    op.drop_column("sys_workspace", "custom_model")
    op.drop_column("sys_workspace", "enable_custom_model")
