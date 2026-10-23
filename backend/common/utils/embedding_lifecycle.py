"""Missing-vector generation with shared worker locks and conditional publication.

Content mutations do not take the worker lock: editing remains available while a
provider is slow. Writers must clear embedding atomically with input changes.
Publication compares that input and requires an empty vector, so a stale response
cannot undo invalidation or replace a newer result. A deleted row stays deleted.
"""

import hashlib

from sqlalchemy import select, text, update

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.embedding.utils import parse_valid_embedding
from common.core.embedding_config import load_embedding_config
from common.utils.utils import SQLBotLogUtil


class EmbeddingGenerationError(RuntimeError):
    """A bounded generation attempt left resources pending for a later retry."""

    def __init__(self, resource: str, ids: list[int]):
        self.resource = resource
        self.ids = tuple(ids)
        super().__init__(f"Embedding generation failed for {resource}: {self.ids}")


def lock_embedding_resource(session, resource: str, resource_id: int) -> None:
    """Serialize workers through commit/rollback, without locking business rows.

    All workers (startup, reenable and resource jobs) use the same resource key.
    Acquire multiple resources in ascending ID order within one resource type.
    PostgreSQL releases transaction locks on rollback, connection loss or death;
    there is no process-local success marker that could hide unfinished work.
    """
    if session.get_bind().dialect.name == "postgresql":
        digest = hashlib.sha256(
            f"sqlbot:embedding:{resource}:{resource_id}".encode()
        ).digest()
        key = int.from_bytes(digest[:8], "big", signed=True)
        session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def generate_missing_embeddings(session_maker, model, input_column, condition=None):
    """Run a knowledge task using its effective config at actual worker start.

    Batch provider calls retain the existing throughput advantage. Lock then
    reread avoids generating vectors already completed by another process. A
    failed batch gets three attempts; failures remain NULL and are reported to
    the Future after other batches have had their chance, never marked complete.
    """
    session = session_maker()
    failed = []
    try:
        if not load_embedding_config(session).enabled:
            return
        query = select(model.id).where(model.embedding.is_(None)).order_by(model.id)
        if condition is not None:
            query = query.where(condition)
        ids = session.execute(query).scalars().all()
        session.commit()
        for start in range(0, len(ids), 32):
            batch = ids[start : start + 32]
            for attempt in range(3):
                try:
                    for resource_id in batch:
                        lock_embedding_resource(
                            session, model.__tablename__, resource_id
                        )
                    # Read scalar tuples, not expiring ORM objects. The exact
                    # original input must survive commits and concurrent edits.
                    inputs = session.execute(
                        select(model.id, input_column)
                        .where(model.id.in_(batch), model.embedding.is_(None))
                        .order_by(model.id)
                    ).all()
                    if inputs:
                        vectors = EmbeddingModelCache.get_model().embed_documents(
                            [value for _, value in inputs]
                        )
                        if len(vectors) != len(inputs):
                            raise ValueError(
                                "Embedding provider returned the wrong vector count"
                            )
                        for (resource_id, original_input), vector in zip(
                            inputs, vectors, strict=True
                        ):
                            vector = parse_valid_embedding(vector)
                            session.execute(
                                update(model)
                                .where(
                                    model.id == resource_id,
                                    input_column == original_input,
                                    model.embedding.is_(None),
                                )
                                .values(embedding=vector)
                            )
                    session.commit()
                    break
                except Exception:
                    session.rollback()
                    if attempt == 2:
                        failed.extend(batch)
                        SQLBotLogUtil.exception(
                            "Embedding generation remains pending for %s: %s",
                            model.__tablename__,
                            batch,
                        )
        if failed:
            raise EmbeddingGenerationError(model.__tablename__, failed)
    finally:
        session_maker.remove()
