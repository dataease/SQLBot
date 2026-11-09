# Issue tracker

新建 spec 或 tickets 前，先询问并确认保存到 GitHub 还是 TAPD，不自行采用默认平台。
当前创建指令已明确平台时视为已确认；每个新的发布批次单独确认，不能仅凭前一批目的地继续创建。

同一已确认批次内的多票创建，以及已有明确位置的更新和附件同步，不逐条重复询问，
也不自动向两个平台发布。读取或更新已有单据时沿用其所在平台。

- GitHub：使用 gh CLI，并显式指定 `--repo dataease/SQLBot`，操作见下文。
- TAPD：先核对当前仓库对应的 TAPD 项目空间及 `workspace_id`；发布和关联操作见 [TAPD 发布约定](tapd.md)。

平台确认可以在整理内容期间提出，但确认前不创建远端单据。

## 资料归属

任务专属的 spec、方案比较、实验报告及实验脚本默认跟随所选平台的规格正文和附件维护，
不默认创建仓库任务目录或提交 Git。本地临时文件只是工作稿，交接入口应是规格链接和附件索引。

Git 保存通用项目约定、长期架构决策、产品维护文档，以及实施后的代码和正式测试资料。
只有用户明确要求或资料确有长期仓库维护用途时，才保留任务资料的 Git 副本，并说明主版本与同步方式。

## GitHub 操作约定

- 创建：`gh issue create --repo dataease/SQLBot --title "..." --body-file <file>`
- 读取：`gh issue view <number> --repo dataease/SQLBot --json number,title,body,labels,comments`
- 列表：`gh issue list --repo dataease/SQLBot --state open --json number,title,body,labels`
- 评论：`gh issue comment <number> --repo dataease/SQLBot --body-file <file>`
- 标签：`gh issue edit <number> --repo dataease/SQLBot --add-label "..."`
  或 `--remove-label "..."`
- 关闭：`gh issue close <number> --repo dataease/SQLBot`

多行正文先写入临时文件，再通过 `--body-file` 传入。
标签角色映射见 `triage-labels.md`。

## Pull requests as a triage surface

**PRs as a request surface: no.**

## 技能用语

- “publish to the issue tracker”：按上面的平台确认结果发布。
- “fetch the relevant ticket”：读取来源单据及完整描述、评论和关联规格。
- `to-spec` 用于综合已确认方案；方案仍待选定时，发布内容应明确标为问题或研究记录。
- `to-tickets` 先审核纵向拆分和依赖，再发布；创建任务不等于开始实现。

## GitHub Wayfinding

地图使用一个带 `wayfinder:map` 标签的 Issue；子任务各建一个 Issue，
使用 `wayfinder:<type>` 标签，type 为 research、prototype、grilling 或 task。

父子关系和阻塞关系优先使用 GitHub 原生功能；不可用时，
在地图正文维护任务列表，在子任务顶部写 `Part of #<map>` 和
`Blocked by: #<number>`。

按地图顺序选择未关闭、无未完成阻塞项且无人认领的任务。
开始前分配给当前开发者；完成后评论结果、关闭任务，
并将结论和链接更新到地图的 Decisions-so-far。
