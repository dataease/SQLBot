from sqlalchemy import update
from sqlmodel import Session, select

from apps.datasource.models.datasource import CoreDatasource
from apps.datasource.utils.utils import (
    DatasourceKeys,
    aes_decrypt,
    aes_encrypt,
    decode_legacy_configuration,
    parse_configuration,
)


def has_versioned_configurations(session: Session) -> bool:
    column = CoreDatasource.__table__.c.configuration
    # Legacy Base64 never contains a colon. Treat unknown versions as encrypted
    # too, so a missing key never triggers a replacement.
    return (
        session.execute(select(column).where(column.contains(":")).limit(1)).first()
        is not None
    )


def migrate_datasource_configurations(session: Session, keys: DatasourceKeys) -> None:
    """Authenticate existing envelopes and migrate legacy or retired-key rows."""
    table = CoreDatasource.__table__
    columns = table.c
    statement = (
        select(columns.id, columns.configuration)
        .where(columns.configuration.is_not(None), columns.configuration != "")
        .order_by(columns.id)
        .limit(100)
    )
    last_id = None
    while True:
        page = statement if last_id is None else statement.where(columns.id > last_id)
        rows = session.execute(page).all()
        if not rows:
            return
        for row_id, old in rows:
            if ":" in old:
                plaintext = aes_decrypt(old, keys)
                if old.split(":", 2)[1] == keys.active:
                    continue
            else:
                plaintext = decode_legacy_configuration(old)
            parse_configuration(plaintext)
            session.execute(
                update(table)
                .where(columns.id == row_id, columns.configuration == old)
                .values(configuration=aes_encrypt(plaintext, keys).decode("ascii"))
            )
        session.commit()
        last_id = rows[-1][0]
