from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import scoped_session, sessionmaker

from common.core.db import engine
from common.utils.metadata_scheduler import MetadataScheduler

executor = ThreadPoolExecutor(max_workers=200)


session_maker = scoped_session(sessionmaker(bind=engine))


# session = session_maker()


def run_save_terminology_embeddings(ids: list[int]):
    from apps.terminology.curd.terminology import save_embeddings

    return executor.submit(save_embeddings, session_maker, ids)


def fill_empty_terminology_embeddings():
    from apps.terminology.curd.terminology import run_fill_empty_embeddings

    return executor.submit(run_fill_empty_embeddings, session_maker)


def run_save_data_training_embeddings(ids: list[int]):
    from apps.data_training.curd.data_training import save_embeddings

    return executor.submit(save_embeddings, session_maker, ids)


def fill_empty_data_training_embeddings():
    from apps.data_training.curd.data_training import run_fill_empty_embeddings

    return executor.submit(run_fill_empty_embeddings, session_maker)


def _run_metadata_batch(table_ids, datasource_ids, scan):
    from apps.datasource.crud.table import run_metadata_embedding_batch

    return run_metadata_embedding_batch(session_maker, table_ids, datasource_ids, scan)


metadata_scheduler = MetadataScheduler(_run_metadata_batch)


def run_save_table_embeddings(ids: list[int]):
    return metadata_scheduler.submit("table", ids)


def run_save_ds_embeddings(ids: list[int]):
    return metadata_scheduler.submit("datasource", ids)


def fill_empty_table_and_ds_embeddings():
    return metadata_scheduler.submit()
