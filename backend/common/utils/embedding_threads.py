from concurrent.futures import ThreadPoolExecutor
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from common.core.config import settings

executor = ThreadPoolExecutor(max_workers=200)

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
session_maker = sessionmaker(bind=engine)
session = session_maker()


def run_save_terminology_embeddings(ids: List[int]):
    from apps.terminology.curd.terminology import save_embeddings
    executor.submit(save_embeddings, session, ids)


def fill_empty_terminology_embeddings():
    from apps.terminology.curd.terminology import run_fill_empty_embeddings
    executor.submit(run_fill_empty_embeddings, session)


def run_save_data_training_embeddings(ids: List[int]):
    from apps.data_training.curd.data_training import save_embeddings
    executor.submit(save_embeddings, session, ids)


def fill_empty_data_training_embeddings():
    from apps.data_training.curd.data_training import run_fill_empty_embeddings
    executor.submit(run_fill_empty_embeddings, session)
