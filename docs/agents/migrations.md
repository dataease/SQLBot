# 数据库迁移 Agent 说明

## 基本规则

- 数据库是 PostgreSQL；SQLModel 变更必须配套 Alembic 迁移。
- 迁移位于 `backend/alembic/versions/`。
- 文件名沿用三位编号加语义描述（存在 `009_0`、`009_1` 子编号形态）；编号从现有迁移文件推导下一个可用值，不要假设固定值。
- 每个迁移必须：
  - 设置唯一 `revision`；
  - 把 `down_revision` 指向当前 head；
  - 提供 `upgrade()` 和可执行的 `downgrade()`；
  - 保持单线迁移链，不创建并行 head。

生成方式：

```bash
cd backend
uv run alembic revision --autogenerate -m "073 describe change"
```

autogenerate 只是草稿。必须人工检查：

- 是否漏掉 xpack 或延迟导入模型的表；
- 索引、约束、默认值、nullable、comment 是否完整；
- 是否包含无关表或历史差异；
- PostgreSQL 方言是否正确，尤其是 `JSONB`、`VECTOR` 和 `USING` 转换。

## 结构迁移

- 新增非空列优先采用两步：先加 nullable 列并回填，再视需要收紧约束。
- 有默认值语义时明确 `server_default`，不要只依赖 Python 模型默认值。
- 修改类型时提供 PostgreSQL `USING` 表达式；参考 `071_modify_permission_jsonb.py`。
- 删除或重命名列先确认代码、导出、报表和 xpack 调用没有旧名残留。
- 不要在迁移里顺手重命名历史表或整理无关 schema。

## 数据迁移

- 数据回填必须分批，避免长事务锁表。
- 先明确空值、重复值和非法历史值的默认策略。
- 不要在迁移中调用业务 CRUD；使用面向迁移的 SQL 或轻量对象。
- 涉及加密、embedding 或外部系统时，说明为什么迁移期可以安全执行。
- downgrade 若无法完整恢复数据，必须显式说明局限，不要伪装成无损回滚。

## xpack schema

- xpack 表结构变更属于跨仓库接口变更。
- 先确认主仓库将锁定的 xpack wheel 版本，并检查该版本中的模型。
- 不要把仅闭源功能需要的表混进开源功能迁移。
- 发布顺序遵循 `docs/agents/packaging.md`。

## 验证

在有可用的一次性开发数据库前，不要默认执行迁移。至少执行：

```bash
cd backend
uv run alembic heads
uv run alembic history
```

确认只有一个 head 且新迁移的父节点正确。对一次性数据库执行 `upgrade head`，必要时再执行一级 downgrade 验证回滚。数据库结构变更要同步检查模型、CRUD、API schema、导出/导入和 xpack 调用。
