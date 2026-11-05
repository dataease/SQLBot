"""Workspace model policy shared by page questions, assistants and MCP."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from apps.system.crud.aimodel_manage import get_ai_model_list_by_workspace
from apps.system.models.system_model import (
    AiModelDetail,
    AiModelWorkspaceMapping,
    AssistantModel,
    WorkspaceModel,
)
from apps.system.schemas.workspace_model import (
    ModelImpact,
    ModelImpactResolution,
    WorkspaceModelSettings,
    WorkspaceModelSettingsOut,
)
from common.audit.models.log_model import SystemLog, SystemLogsResource
from common.error import SingleMessageError
from common.utils.locale import I18nHelper

if TYPE_CHECKING:
    from apps.system.schemas.system_schema import AssistantHeader, UserInfoDTO

ModelSettingsSnapshot = dict[str, bool | str | None]


def record_model_settings_change(
    session: Session,
    workspace: WorkspaceModel,
    before: ModelSettingsSnapshot,
    after: ModelSettingsSnapshot,
    actor: UserInfoDTO | None,
    trans: I18nHelper,
) -> None:
    # Commit the audit entry with the configuration/mapping transaction.
    if actor is not None:
        log = SystemLog(
            operation_type="update",
            operation_status="success",
            module="workspace",
            operation_detail=trans("ws_model_settings"),
            resource_id=str(workspace.id),
            resource_name=workspace.name,
            oid=workspace.id,
            user_id=actor.id,
            user_name=actor.name,
            remark=json.dumps({"before": before, "after": after}),
        )
        session.add(log)
        session.flush()
        session.add(
            SystemLogsResource(
                log_id=log.id,
                resource_id=str(workspace.id),
                resource_name=workspace.name,
                module="workspace",
            )
        )


def require_authorized_model(
    session: Session, workspace_id: int, model_id: str | int | None, trans: I18nHelper
) -> int:
    try:
        if isinstance(model_id, bool):
            raise ValueError
        value = int(str(model_id))
        if not 0 < value <= 2**63 - 1:
            raise ValueError
    except (ValueError, TypeError):
        raise SingleMessageError(trans("i18n_llm.model_unavailable"))
    model = session.exec(
        select(AiModelDetail)
        .join(
            AiModelWorkspaceMapping,
            AiModelWorkspaceMapping.ai_model_id == AiModelDetail.id,
        )
        .where(
            AiModelDetail.id == value,
            AiModelWorkspaceMapping.workspace_id == workspace_id,
        )
    ).first()
    if model is None:
        raise SingleMessageError(trans("i18n_llm.model_unavailable"))
    return value


def resolve_model_id(
    session: Session,
    workspace_id: int,
    trans: I18nHelper,
    assistant: AssistantHeader | None = None,
    custom_model: str | int | None = None,
) -> int:
    workspace = session.get(WorkspaceModel, workspace_id)
    if workspace is None:
        raise SingleMessageError(trans("i18n_llm.workspace_unavailable"))
    # An explicitly empty workspace default disables every model invocation,
    # including assistants and MCP requests that supply their own model.
    if workspace.enable_custom_model and not workspace.custom_model:
        raise SingleMessageError(trans("i18n_llm.workspace_disabled"))
    if custom_model is not None and custom_model != "":
        return require_authorized_model(session, workspace_id, custom_model, trans)
    if assistant and assistant.enable_custom_model:
        return require_authorized_model(
            session, workspace_id, assistant.custom_model, trans
        )
    if workspace.enable_custom_model:
        return require_authorized_model(
            session, workspace_id, workspace.custom_model, trans
        )
    model = session.exec(
        select(AiModelDetail).where(AiModelDetail.default_model.is_(True))
    ).first()
    if model is None:
        raise SingleMessageError(trans("i18n_llm.miss_default"))
    return model.id


def get_workspace_model_settings(
    session: Session, workspace: WorkspaceModel
) -> WorkspaceModelSettingsOut:
    models = get_ai_model_list_by_workspace(session, workspace.id, False)
    return WorkspaceModelSettingsOut(
        enable_custom_model=workspace.enable_custom_model,
        custom_model=workspace.custom_model,
        models=models,
        model_valid=any(str(item.id) == workspace.custom_model for item in models),
    )


def save_workspace_model_settings(
    session: Session,
    workspace: WorkspaceModel,
    settings: WorkspaceModelSettings,
    trans: I18nHelper,
    actor: UserInfoDTO | None = None,
) -> dict[str, ModelSettingsSnapshot]:
    if settings.enable_custom_model and settings.custom_model:
        require_authorized_model(session, workspace.id, settings.custom_model, trans)
    before = WorkspaceModelSettings.model_validate(
        workspace, from_attributes=True
    ).model_dump()
    workspace.enable_custom_model = settings.enable_custom_model
    workspace.custom_model = (
        settings.custom_model if settings.enable_custom_model else None
    )
    session.add(workspace)
    changes: dict[str, ModelSettingsSnapshot] = {
        "before": before,
        "after": WorkspaceModelSettings.model_validate(
            workspace, from_attributes=True
        ).model_dump(),
    }
    record_model_settings_change(
        session, workspace, changes["before"], changes["after"], actor, trans
    )
    session.commit()
    return changes


def get_model_impacts(
    session: Session,
    model_id: int,
    ws_ids: list[int] | None = None,
    *,
    lock: bool = False,
) -> list[ModelImpact]:
    statement = select(WorkspaceModel).order_by(WorkspaceModel.id)
    if ws_ids is not None:
        statement = statement.where(WorkspaceModel.id.in_(ws_ids))
    if lock:
        statement = statement.with_for_update()
    workspaces = session.exec(statement).all()
    assistants = session.exec(
        select(AssistantModel).where(
            AssistantModel.enable_custom_model.is_(True),
            AssistantModel.custom_model == str(model_id),
        )
    ).all()
    result = []
    for workspace in workspaces:
        uses_default = workspace.enable_custom_model and workspace.custom_model == str(
            model_id
        )
        names = [item.name for item in assistants if item.oid == workspace.id]
        if uses_default or names:
            result.append(
                ModelImpact(
                    workspace_id=str(workspace.id),
                    workspace_name=workspace.name,
                    uses_default=uses_default,
                    assistants=names,
                    models=[
                        item
                        for item in get_ai_model_list_by_workspace(
                            session, workspace.id, False
                        )
                        if item.id != model_id
                    ],
                )
            )
    return result


def apply_model_impact_resolutions(
    session: Session,
    model_id: int,
    ws_ids: list[int] | None,
    resolutions: list[ModelImpactResolution],
    trans: I18nHelper,
    actor: UserInfoDTO | None = None,
) -> None:
    # Recompute at mutation time; an earlier preview is never authorization.
    impacts = get_model_impacts(session, model_id, ws_ids, lock=True)
    resolution_map = {item.workspace_id: item for item in resolutions}
    if len(resolution_map) != len(resolutions) or set(resolution_map) != {
        int(item.workspace_id) for item in impacts
    }:
        raise SingleMessageError(trans("i18n_llm.impact_confirmation_required"))
    changes = []
    # Validate the entire batch before changing any workspace or mapping.
    for impact in impacts:
        resolution = resolution_map[int(impact.workspace_id)]
        if resolution.custom_model is not None:
            replacement = require_authorized_model(
                session, resolution.workspace_id, resolution.custom_model, trans
            )
            if not impact.uses_default or replacement == model_id:
                raise SingleMessageError(trans("i18n_llm.model_unavailable"))
            changes.append((resolution.workspace_id, str(replacement)))
    for workspace_id, replacement in changes:
        workspace = session.get(WorkspaceModel, workspace_id)
        before = WorkspaceModelSettings.model_validate(
            workspace, from_attributes=True
        ).model_dump()
        workspace.custom_model = replacement
        session.add(workspace)
        after = WorkspaceModelSettings.model_validate(
            workspace, from_attributes=True
        ).model_dump()
        record_model_settings_change(session, workspace, before, after, actor, trans)
