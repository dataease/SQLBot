"""Deterministic external embedding adapter and public metadata reader for tests."""

from types import SimpleNamespace


def metadata_model(vector=None, *, embed=None, limit=128):
    encode = embed or (lambda _value: vector or [1.0, 0.0])
    return SimpleNamespace(
        embed_query=encode,
        embed_documents=lambda texts: [encode(text) for text in texts],
        _client=SimpleNamespace(
            _first_module=lambda: SimpleNamespace(
                max_seq_length=limit,
                do_lower_case=False,
                tokenizer=lambda text, **_kwargs: {"input_ids": [0, *list(text), 1]},
            )
        ),
    )


def read_table_vectors(session, table_id):
    from apps.datasource.crud.table import _table_input
    from apps.datasource.embedding.metadata_chunks import read_metadata
    from apps.datasource.models.datasource import CoreTable

    table = session.get(CoreTable, table_id)
    return read_metadata(session, "table", table_id, _table_input(session, table))


def read_datasource_vectors(session, datasource_id):
    from apps.datasource.crud.table import _resource_input
    from apps.datasource.embedding.metadata_chunks import read_metadata
    from apps.datasource.models.datasource import CoreDatasource

    datasource = session.get(CoreDatasource, datasource_id)
    return read_metadata(
        session, "datasource", datasource_id, _resource_input(session, datasource)
    )
