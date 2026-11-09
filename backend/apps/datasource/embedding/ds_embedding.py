"""Vector preselection of already-authorized datasource candidates."""

import traceback

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.embedding.metadata_chunks import read_metadata
from apps.datasource.embedding.utils import (
    batch_cosine_similarity,
    parse_valid_embedding,
)
from apps.datasource.models.datasource import CoreDatasource
from apps.system.crud.assistant import AssistantOutDs
from common.core.deps import CurrentAssistant, SessionDep
from common.core.embedding_config import EmbeddingConfig, load_embedding_config
from common.utils.utils import SQLBotLogUtil


def get_ds_embedding(
    session: SessionDep,
    _ds_list,
    out_ds: AssistantOutDs,  # noqa: ARG001 - retained for existing callers
    question: str,
    current_assistant: CurrentAssistant | None = None,
    *,
    config: EmbeddingConfig | None = None,
):
    # Advanced applications keep their existing model-only datasource selection.
    if current_assistant and current_assistant.type in (1, 3):
        return _ds_list
    config = config or load_embedding_config(session)
    if not config.table_enabled or len(_ds_list) <= 1:
        return _ds_list
    try:
        from apps.datasource.crud.table import _resource_input

        vectors = []
        for candidate in _ds_list:
            datasource = session.get(CoreDatasource, candidate.get("id"))
            if datasource is None:
                raise ValueError("Missing metadata datasource")
            vectors.append(
                read_metadata(
                    session,
                    "datasource",
                    datasource.id,
                    _resource_input(session, datasource),
                )
            )
        query = parse_valid_embedding(
            EmbeddingModelCache.get_model().embed_query(question)
        )
        if any(len(vector) != len(query) for chunks in vectors for vector in chunks):
            raise ValueError("Query and metadata dimensions differ")
        ranked = sorted(
            zip(_ds_list, vectors, strict=True),
            key=lambda item: float(max(batch_cosine_similarity(query, item[1]))),
            reverse=True,
        )
        selected = [
            candidate for candidate, _vector in ranked[: config.datasource_count]
        ]
        SQLBotLogUtil.info(
            f"[embedding] stage=datasource action=vector_selection "
            f"candidate_count={len(_ds_list)} result_count={len(selected)} "
            f"limit={config.datasource_count}"
        )
        return selected
    except Exception as exc:
        traceback.print_exc()
        SQLBotLogUtil.info(
            f"[embedding] stage=datasource action=fallback "
            f"reason=invalid_vectors_or_scoring_failed error_type={type(exc).__name__} "
            f"candidate_count={len(_ds_list)} result_count={len(_ds_list)}"
        )
        # Incomplete/stale vectors or a failed model must not remove candidates,
        # nor return ORM/internal fields in the model-facing candidate DTOs.
        return _ds_list
