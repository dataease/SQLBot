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

### Impala / Hive Kerberos 认证

Hive / Impala 数据源可在编辑表单开启 Kerberos，填写客户端 principal 和服务名，上传 krb5.conf（最多 64 KiB）及 keytab（最多 256 KiB）。服务名默认分别为 hive / impala；host 必须与服务 principal 对应，Impala 的 HiveServer2 端口通常为 21050。用户名是会话用户名，实际认证身份来自客户端 principal/keytab，不应上传 Hive/Impala 服务端账号的 keytab。

每个数据源的上传内容随连接配置使用 AES-256-GCM 加密存储，不新增明文持久文件；编辑详情只返回已配置状态，不返回文件内容。编辑时留空沿用，连接目标或认证参数改变时必须重新提供凭据。关闭 Kerberos 会清除该数据源保存的 conf/keytab；删除数据源同时删除加密配置。备份及恢复必须保留部署的数据源存储密钥。浏览器上传仍使用已有兼容编码，生产环境必须通过 HTTPS 保护传输。

每次建立 Kerberos 连接都在独立子进程中创建权限为 0700 的临时目录，文件权限为 0600，使用 kinit -kt 自动获取新票据，再用 PyHive 建立连接。查询结束、超时或失败时停止子进程并清理目录，不更改 API/MCP 父进程环境，也不共用部署票据缓存。当前策略不复用 Kerberos 长连接池，不需要后台定时续期：下一次连接自动重新认证；单次连接操作受数据源超时（最多 300 秒）限制。每个 API/MCP 进程最多同时运行 8 个此类连接；其余请求有界等待。异常关机可能留下临时目录，由部署侧临时目录清理策略处理。

上传配置只接受 libdefaults、realms、domain_realm 三个区段的受限参数（校验入口 apps/db/kerberos_connection.py）。不支持 include/includedir、插件、自定义文件路径、auth_to_local 或系统级配置覆盖；应上传不包含这些内容的最小客户端配置。当前上传认证模式仅支持 HiveServer2 二进制 TCP，不支持额外连接参数/TLS/HTTP；需要这些模式时应先适配传输参数，不能通过关闭证书验证绕过。

部署仍需安装 kinit、Kerberos/GSSAPI 运行库和 Python kerberos 模块，并保证 DNS、时间同步及 KDC/数据源网络可达。backend/pyproject.toml 已声明 Python 依赖；应用 Dockerfile 安装 krb5-user 和 libgssapi-krb5-2，构建基础镜像需具备现有 libkrb5-dev。使用当前源码重新构建镜像后生效，官方旧镜像不包含这些改动。本地开发应在 backend 下运行 uv sync 安装依赖；macOS 需准备对应 Kerberos 开发工具链。

保留原有额外参数 auth=KERBEROS&kerberos_service_name=impala（Hive 使用 hive）的部署侧票据缓存模式；只有打开表单 Kerberos 开关时才启用上传和自动获取模式。

离线回归以合成 kinit/驱动验证身份隔离、加密凭据保留和清理，不代表已完成真实集群握手。上线前需验证测试连接、表/字段读取、查询、错误 keytab/KDC 不可达、替换凭据及删除数据源；实际 Impala/Hive 版本、TLS 和授权策略需在目标环境验收。

Kerberos 服务主机名为 Hive/Impala 共用的选填字段：留空时使用连接主机，填写后仅作为 SASL 服务身份中的主机名，TCP 地址保持不变。例如连接 47.104.211.244、认证主机 impala.impala.test。修改该认证目标时必须重新上传凭据。

KDC 地址支持受限的 tcp/host:port、udp/host:port 写法（仅限 realms 区段的 kdc 项），可用于 macOS 客户端明确指定传输协议。

Impala SQL 模板按实际版本选择函数、表达式及查询结构，不固定版本范围或函数白名单。可使用当前版本内置函数，以及上下文明确提供签名和用途的 UDF/UDAF；版本未知时优先采用已知成熟语法，对不确定能力明确说明。不保证所有版本或函数均已实机验收，也不会自动检索外部函数文档。Kerberos 工作进程在认证成功后将数据库执行错误单独返回，保留受限长度、已过滤凭据/临时路径的数据库诊断；认证与建连失败仍返回通用错误。

Impala 的提示词引擎信息通过内部 SELECT VERSION() 获取实际版本，通过现有 <Info>/<db-engine> 进入提示词，Impala 的 other_rule 引用该引擎信息；获取失败时采用版本未知策略。Impala 模板明确区分认证/连接协议与 SQL 方言，要求历史示例和召回 SQL 服从实际版本。修改模板后需要重启后端以清除模板缓存。
