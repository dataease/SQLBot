# FastAPI Project - Backend

## 表检查启动参数

`SQLBOT_SKIP_TABLE_CHECK` 默认为 `false`。不配置时，生成的 SQL 仍通过真实表名提取和本轮允许表集合检查。

仅在需要跳过表白名单检查时设置：

```dotenv
SQLBOT_SKIP_TABLE_CHECK=true
```

通过进程环境变量传入；本地开发也可写入仓库根目录 `.env`，安装版可写入安装目录的 `conf/sqlbot.conf`。Docker Compose 部署可在 SQLBot 服务的 `environment` 中设置。修改后需重启服务或重建容器，所有问数入口共用该启动配置，不提供配置页面或运行时修改。

开启后仅跳过表白名单检查，可能允许查询数据源账号可读取的未勾选表。真实表名提取始终执行，无法提取表名时仍拒绝 SQL。SQL 只读、危险函数、元数据查询控制、行权限处理及行数限制仍按原有流程执行。

## 数据源存储密钥

默认无需配置。API 首次启动时会在持久化目录 `UPLOAD_DIR/.secrets/datasource-keys.json` 自动生成部署专用密钥，默认完整路径为 `/opt/sqlbot/data/file/.secrets/datasource-keys.json`。保留现有 `file` 数据卷，API 和 MCP 使用同一文件。若数据库已有新版密文而密钥文件缺失，启动会停止，请恢复原密钥文件。

使用外部 secret 管理时，可以通过 `SQLBOT_DATASOURCE_KEYS_FILE` 指向已有的只读密钥文件。文件格式如下，其中 `active` 是当前写入使用的密钥标识，`keys` 的值是 32 字节随机密钥的标准 Base64：

```json
{"active":"primary","keys":{"primary":"<base64-encoded-32-byte-key>"}}
```

使用外部 secret 管理时，可在受控目录内用下列命令创建新文件。命令拒绝覆盖现有文件，生成值只写入文件。

```sh
umask 077
python3 -c 'import base64,json,secrets; key=base64.b64encode(secrets.token_bytes(32)).decode(); json.dump({"active":"primary","keys":{"primary":key}},open("datasource-keys.json","x"))'
```

升级前备份数据库和密钥文件，分开加密保存并限制访问。停止旧版 API、MCP 和其他写入进程后启动新版 API，等待启动迁移完成，再启用 MCP 和流量。API 启动时校验密钥和现存密文，并分批把旧 ECB 配置转换为 AES-256-GCM。每批提交后可以重启续跑。更新比较读取时的原值，保留期间已被编辑的行。遇到缺失密钥或损坏密文时启动会失败，当前批次回滚。恢复正确的密钥或数据库记录后重启。新旧程序混跑会造成格式不兼容。回退旧程序需要受控恢复升级前的数据库备份，并评估升级后的数据变更。

轮换时先停止该部署的 API 和 MCP，保留旧密钥，加入新密钥并将 `active` 切换到新标识，原子替换文件。启动 API，等待现有配置重新加密，再恢复其他进程。用当前密钥文件验证数据库备份恢复后，可从在线文件移除旧密钥。历史备份所需密钥应离线保留至备份过期。恢复时先准备匹配该备份的密钥文件，再启动 API。已暴露的旧 ECB 密文仍可解密，应轮换对应数据源自身的凭据。

浏览器写入仍兼容旧请求编码，部署通过 HTTPS 保护传输。数据源列表和写入响应省略配置，授权编辑详情仅提供表单字段，密码和额外连接参数留空表示沿用。连接目标变化时需要重新提供已保存的敏感连接字段。API 客户端可发送显式空字符串清除密码或额外连接参数。
