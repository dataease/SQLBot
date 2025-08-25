<p align="center"><img src="https://resource-fit2cloud-com.oss-cn-hangzhou.aliyuncs.com/sqlbot/sqlbot.png" alt="SQLBot" width="300" /></p>
<h3 align="center">基于大模型和 RAG 的智能问数系统</h3>
<p align="center">
  <a href="https://github.com/dataease/SQLBot/releases/latest"><img src="https://img.shields.io/github/v/release/dataease/SQLBot" alt="Latest release"></a>
  <a href="https://github.com/dataease/SQLBot"><img src="https://img.shields.io/github/stars/dataease/SQLBot?color=%231890FF&style=flat-square" alt="Stars"></a>    
  <a href="https://hub.docker.com/r/dataease/SQLbot"><img src="https://img.shields.io/docker/pulls/dataease/sqlbot?label=downloads" alt="Download"></a><br/>

</p>
<hr/>

SQLBot 是一款基于大模型和 RAG 的智能问数系统。SQLBot 的优势包括：

- **开箱即用**: 只需配置大模型和数据源即可开启问数之旅，通过大模型和 RAG 的结合来实现高质量的 text2sql；
- **易于集成**: 支持快速嵌入到第三方业务系统，也支持被 n8n、MaxKB、Dify、Coze 等 AI 应用开发平台集成调用，让各类应用快速拥有智能问数能力；
- **安全可控**: 提供基于工作空间的资源隔离机制，能够实现细粒度的数据权限控制。

## 快速开始

### 安装部署

准备一台 Linux 服务器，执行以下一键安装脚本。  
在运行 SQLBot 前，请确保已安装好 [Docker](https://docs.docker.com/get-docker/) 和 [Docker Compose](https://docs.docker.com/compose/install/)。

```bash
# 创建目录
mkdir -p /opt/sqlbot
cd /opt/sqlbot

# 下载 docker-compose.yaml
curl -o docker-compose.yaml https://raw.githubusercontent.com/dataease/SQLBot/main/docker-compose.yaml

# 启动服务
docker compose up -d
```

你也可以通过 [1Panel 应用商店](https://apps.fit2cloud.com/1panel) 快速部署 SQLBot；

### 访问方式

- 在浏览器中打开: http://<你的服务器IP>:8000/
- 用户名: admin
- 密码: SQLBot@123456

### 联系我们

如你有更多问题，可以加入我们的技术交流群与我们交流。

<img width="180" height="180" alt="contact_me_qr" src="https://github.com/user-attachments/assets/2594ff29-5426-4457-b051-279855610030" />

## UI 展示

  <tr>
    <img alt="q&a" src="https://github.com/user-attachments/assets/55526514-52f3-4cfe-98ec-08a986259280"   />
  </tr>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dataease/sqlbot&type=Date)](https://www.star-history.com/#dataease/sqlbot&Date)

## 飞致云旗下的其他明星项目

- [DataEase](https://github.com/dataease/dataease/) - 人人可用的开源 BI 工具
- [1Panel](https://github.com/1panel-dev/1panel/) - 现代化、开源的 Linux 服务器运维管理面板
- [MaxKB](https://github.com/1panel-dev/MaxKB/) - 强大易用的企业级智能体平台
- [JumpServer](https://github.com/jumpserver/jumpserver/) - 广受欢迎的开源堡垒机
- [Halo](https://github.com/halo-dev/halo/) - 强大易用的开源建站工具
- [MeterSphere](https://github.com/metersphere/metersphere/) - 新一代的开源持续测试工具

## License

本仓库遵循 [FIT2CLOUD Open Source License](LICENSE) 开源协议，该许可证本质上是 GPLv3，但有一些额外的限制。
