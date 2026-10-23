# Issue tracker: GitHub

本仓库的 Issue 和规格维护在 dataease/SQLBot 的 GitHub Issues。
使用 gh CLI，并显式指定 `--repo dataease/SQLBot`。

## 操作约定

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

- “publish to the issue tracker”：创建 GitHub Issue。
- “fetch the relevant ticket”：读取对应 Issue 及评论。

## Wayfinding

地图使用一个带 `wayfinder:map` 标签的 Issue；子任务各建一个 Issue，
使用 `wayfinder:<type>` 标签，type 为 research、prototype、grilling 或 task。

父子关系和阻塞关系优先使用 GitHub 原生功能；不可用时，
在地图正文维护任务列表，在子任务顶部写 `Part of #<map>` 和
`Blocked by: #<number>`。

按地图顺序选择未关闭、无未完成阻塞项且无人认领的任务。
开始前分配给当前开发者；完成后评论结果、关闭任务，
并将结论和链接更新到地图的 Decisions-so-far。
