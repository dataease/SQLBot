"""Complete, tokenizer-bounded metadata representations and atomic internal storage."""

import copy
import hashlib
import json
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from apps.datasource.embedding.utils import (
    batch_cosine_similarity,
    parse_valid_embedding,
)
from apps.datasource.models.metadata_embedding import MetadataEmbedding
from common.core.config import settings

FORMAT_VERSION = 1


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def model_id() -> str:
    # The deployed model is immutable for a running service (see embedding ADR).
    return settings.DEFAULT_EMBEDDING_MODEL


def chunk_text(text: str, model: Any) -> list[str]:
    """Preserve every character, preferring field lines before splitting long lines.

    HuggingFaceEmbeddings replaces newlines; SentenceTransformer's Transformer
    strips and optionally lowercases text before tokenizing. Count that exact
    tokenizer input including special tokens, without truncation.
    """
    transformer = model._client._first_module()
    limit = transformer.max_seq_length
    # Fast tokenizers mutate truncation state on each call. Counting must not
    # race with shared model inference (including queries and datasource jobs).
    tokenizer = copy.deepcopy(transformer.tokenizer)

    def token_count(value: str) -> int:
        value = value.replace("\n", " ").strip()
        if transformer.do_lower_case:
            value = value.lower()
        return len(
            tokenizer(value, truncation=False, add_special_tokens=True, verbose=False)[
                "input_ids"
            ]
        )

    def fits(value: str) -> bool:
        return token_count(value) <= limit

    first_line = text.splitlines(keepends=True)[0] if text else ""
    context = first_line if token_count(first_line) <= min(32, limit // 4) else ""
    chunks: list[str] = []
    bodies: list[str] = []
    current = ""

    def prefix() -> str:
        return context if chunks else ""

    def emit(body: str) -> None:
        chunks.append(prefix() + body)
        bodies.append(body)

    for line in text.splitlines(keepends=True):
        if fits(prefix() + current + line):
            current += line
            continue
        if current:
            emit(current)
            current = ""
        while line and not fits(prefix() + line):
            low, high = 0, len(line)
            while low < high:
                middle = (low + high + 1) // 2
                if fits(prefix() + line[:middle]):
                    low = middle
                else:
                    high = middle - 1
            if not low:
                raise ValueError("Model cannot encode one metadata character")
            emit(line[:low])
            line = line[low:]
        current = line
    if current:
        emit(current)
    if (
        not chunks
        or "".join(bodies) != text
        or not all(fits(chunk) for chunk in chunks)
    ):
        raise ValueError("Incomplete metadata input")
    return chunks


def encode_metadata(text: str, model: Any) -> list[list[float]]:
    chunks = chunk_text(text, model)
    vectors: list[list[float]] = []
    for start in range(0, len(chunks), 32):
        batch = chunks[start : start + 32]
        result = model.embed_documents(batch)
        if len(result) != len(batch):
            raise ValueError("Incomplete metadata encoding")
        vectors.extend(parse_valid_embedding(vector) for vector in result)
    dimension = len(vectors[0])
    if any(len(vector) != dimension for vector in vectors):
        raise ValueError("Inconsistent metadata dimensions")
    return vectors


def publish_metadata(
    session: Session,
    resource_type: str,
    resource_id: int,
    text: str,
    vectors: list[list[float]],
) -> None:
    encoded = json.dumps(vectors, allow_nan=False)
    session.merge(
        MetadataEmbedding(
            resource_type=resource_type,
            resource_id=resource_id,
            format_version=FORMAT_VERSION,
            model_id=model_id(),
            input_hash=fingerprint(text),
            chunk_count=len(vectors),
            dimension=len(vectors[0]),
            vectors_hash=fingerprint(encoded),
            vectors=encoded,
        )
    )


def read_metadata(
    session: Session, resource_type: str, resource_id: int, text: str
) -> list[list[float]]:
    record = session.get(MetadataEmbedding, (resource_type, resource_id))
    if (
        record is None
        or record.format_version != FORMAT_VERSION
        or record.model_id != model_id()
        or record.input_hash != fingerprint(text)
        or record.chunk_count < 1
        or fingerprint(record.vectors) != record.vectors_hash
    ):
        raise ValueError("Missing or stale metadata representation")
    vectors = json.loads(record.vectors)
    if not isinstance(vectors, list) or len(vectors) != record.chunk_count:
        raise ValueError("Incomplete metadata representation")
    vectors = [parse_valid_embedding(vector) for vector in vectors]
    if any(len(vector) != record.dimension for vector in vectors):
        raise ValueError("Inconsistent metadata dimensions")
    return vectors


def invalidate_chunks(session: Session, resource_type: str, ids: list[int]) -> None:
    session.execute(
        delete(MetadataEmbedding).where(
            MetadataEmbedding.resource_type == resource_type,
            MetadataEmbedding.resource_id.in_(ids),
        )
    )


def table_scores(
    session: Session, tables: list[dict[str, Any]], query_embedding: Any
) -> list[float]:
    # Only caller-authorized IDs are loaded. Fingerprints use persisted metadata,
    # not the permission-filtered schema rendered for this particular user.
    from apps.datasource.crud.table import _table_input
    from apps.datasource.models.datasource import CoreTable

    query = parse_valid_embedding(query_embedding)
    scores = []
    for candidate in tables:
        table = session.get(CoreTable, candidate["id"])
        if table is None:
            raise ValueError("Missing metadata table")
        vectors = read_metadata(
            session, "table", table.id, _table_input(session, table)
        )
        if any(len(vector) != len(query) for vector in vectors):
            raise ValueError("Query and metadata dimensions differ")
        scores.append(float(max(batch_cosine_similarity(query, vectors))))
    return scores
