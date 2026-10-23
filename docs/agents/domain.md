# Domain Docs

本仓库采用 single-context 布局。

## 阅读入口

探索相关领域前：

- 读取根目录 `CONTEXT.md`：它是本仓库的领域词汇表，
  对应工程技能默认称作 GLOSSARY.md 的文档。
- 若 `docs/adr/` 存在，读取与当前任务相关的架构决策。
- 领域边界尚不明确时，按 `AGENTS.md` 查阅
  `docs/agents/domain-open-questions.md`。

## 维护约定

- 技能要求读取或更新 GLOSSARY.md 时，操作 `CONTEXT.md`。
- Issue、设计建议和测试命名使用 `CONTEXT.md` 中定义的术语。
- 术语缺口先核实；稳定定义补入 `CONTEXT.md`。
- ADR 在实际形成架构决策时按需创建，保存为
  `docs/adr/NNNN-<slug>.md`；缺少目录时继续当前任务。
- 建议与既有 ADR 冲突时，明确指出冲突及重新讨论的理由。
