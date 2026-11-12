# FastAPI Project - Backend

## 表检查启动参数

`SQLBOT_SKIP_TABLE_CHECK` 默认为 `false`。不配置时，生成的 SQL 仍通过真实表名提取和本轮允许表集合检查。

仅在需要跳过表白名单检查时设置：

```dotenv
SQLBOT_SKIP_TABLE_CHECK=true
```

通过进程环境变量传入；本地开发也可写入仓库根目录 `.env`，安装版可写入安装目录的 `conf/sqlbot.conf`。Docker Compose 部署可在 SQLBot 服务的 `environment` 中设置。修改后需重启服务或重建容器，所有问数入口共用该启动配置，不提供配置页面或运行时修改。

开启后仅跳过表白名单检查，可能允许查询数据源账号可读取的未勾选表。真实表名提取始终执行，无法提取表名时仍拒绝 SQL。SQL 只读、危险函数、元数据查询控制、行权限处理及行数限制仍按原有流程执行。
