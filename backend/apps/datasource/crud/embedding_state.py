"""Atomic metadata invalidation. Lock parents before children in every writer."""

from sqlalchemy import update

from apps.datasource.models.datasource import CoreDatasource, CoreTable


def invalidate_metadata(session, ds_id: int, table_ids=()):
    # These row locks also serialize the short validation/publication phase of
    # generation. No business row is locked while the model provider is running.
    session.execute(
        update(CoreDatasource).where(CoreDatasource.id == ds_id).values(embedding=None)
    )
    if table_ids:
        session.execute(
            update(CoreTable)
            .where(CoreTable.ds_id == ds_id, CoreTable.id.in_(table_ids))
            .values(embedding=None)
        )
