"""Protect dormant local credentials with salted Argon2id.

Irreversible data migration: never downgrade credentials back to MD5. Stop old
writers before upgrading. Each CAS update commits independently so interruption
is resumable; historical initialization scripts remain unchanged.
"""

import sqlalchemy as sa

from alembic import op
from common.core.passwords import is_legacy_password, wrap_legacy_password

revision = "d91543ca7b21"
down_revision = "ed42b7f169a3"
branch_labels = None
depends_on = None
BATCH_SIZE = 100


def upgrade():
    # No external services, configuration, CRUD or plaintext passwords are used.
    # Release row locks after each update rather than holding them during hashing.
    with op.get_context().autocommit_block():
        bind = op.get_bind()
        schema = None
        if bind.dialect.name == "postgresql":
            schema = bind.scalar(sa.text("SELECT current_schema()"))
            if not schema or not sa.inspect(bind).has_table("sys_user", schema=schema):
                raise RuntimeError(
                    "Local credentials must exist in the current migration schema"
                )
        users = sa.table(
            "sys_user",
            sa.column("id", sa.BigInteger),
            sa.column("password", sa.String(255)),
            schema=schema,
        )
        last_id = None
        while True:
            query = (
                sa.select(users.c.id, users.c.password)
                .order_by(users.c.id)
                .limit(BATCH_SIZE)
            )
            if last_id is not None:
                query = query.where(users.c.id > last_id)
            rows = bind.execute(query).all()
            if not rows:
                break
            for uid, stored in rows:
                if is_legacy_password(stored):
                    replacement = wrap_legacy_password(stored)
                    bind.execute(
                        users.update()
                        .where(users.c.id == uid, users.c.password == stored)
                        .values(password=replacement)
                    )
            last_id = rows[-1][0]


def downgrade():
    # Schema is unchanged. Keeping strong credentials is intentional; old
    # applications are incompatible and require a coordinated restore/reset.
    pass
