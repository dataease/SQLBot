<p align="center"><img src="https://resource-fit2cloud-com.oss-cn-hangzhou.aliyuncs.com/sqlbot/sqlbot.png" alt="SQLBot" width="300" /></p>
<h3 align="center">Intelligent Questioning System Based on Large Models and RAG</h3>
<p align="center">
  <a href="https://trendshift.io/repositories/14540" target="_blank"><img src="https://trendshift.io/api/badge/repositories/14540" alt="dataease%2FSQLBot | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
</p>

<p align="center">
  <a href="https://github.com/dataease/SQLBot/releases/latest"><img src="https://img.shields.io/github/v/release/dataease/SQLBot" alt="Latest release"></a>
  <a href="https://github.com/dataease/SQLBot"><img src="https://img.shields.io/github/stars/dataease/SQLBot?color=%231890FF&style=flat-square" alt="Stars"></a>    
  <a href="https://hub.docker.com/r/dataease/SQLbot"><img src="https://img.shields.io/docker/pulls/dataease/sqlbot?label=downloads" alt="Download"></a><br/>
</p>

<p align="center">
  <a href="README.md"><img alt="中文(简体)" src="https://img.shields.io/badge/中文(简体)-d9d9d9"></a>
  <a href="/docs/README.en.md"><img alt="English" src="https://img.shields.io/badge/English-d9d9d9"></a>
</p>
<hr/>

SQLBot is an intelligent data query system based on large language models and RAG, meticulously crafted by the DataEase open-source project team. With SQLBot, users can perform conversational data analysis (ChatBI), quickly extracting the necessary data information and visualizations, and supporting further intelligent analysis.

## How It Works

<img width="1105" height="577" alt="image" src="https://github.com/user-attachments/assets/58f147ff-412e-4ac9-a450-5d01a0bbe9f6" />


## Key Features

- **Out-of-the-Box Functionality:** Simply configure the large model and data source; no complex development is required to quickly enable intelligent data collection. Leveraging the large model's natural language understanding and SQL generation capabilities, combined with RAG technology, it achieves high-quality Text-to-SQL conversion.
- **Secure and Controllable:** Provides a workspace-level resource isolation mechanism, building clear data boundaries and ensuring data access security. Supports fine-grained data permission configuration, strengthening permission control capabilities and ensuring compliance and controllability during use.
- **Easy Integration:** Supports multiple integration methods, providing capabilities such as web embedding, pop-up embedding, and MCP invocation. It can be quickly embedded into applications such as n8n, Dify, MaxKB, and DataEase, allowing various applications to quickly acquire intelligent data collection capabilities.
- **Increasingly Accurate with Use:** Supports customizable prompts and terminology library configurations, maintainable SQL example calibration logic, and accurate matching of business scenarios. Efficient operation, based on continuous iteration and optimization using user interaction data, the data collection effect gradually improves with use, becoming more accurate with each use.

## Supported LLM Providers

| Provider | API Compatibility |
|----------|-------------------|
| Alibaba Cloud Bailian | OpenAI Compatible |
| Qianfan Model | OpenAI Compatible |
| DeepSeek | OpenAI Compatible |
| Tencent Hunyuan | OpenAI Compatible |
| iFlytek Spark | OpenAI Compatible |
| Gemini | OpenAI Compatible |
| OpenAI | Native |
| Kimi | OpenAI Compatible |
| Tencent Cloud | OpenAI Compatible |
| Volcano Engine | OpenAI Compatible |
| MiniMax | OpenAI Compatible |
| Generic OpenAI Compatible | Custom |

## Quick Start

### Installation and Deployment

Prepare a Linux server, install [Docker](https://docs.docker.com/get-docker/), and execute the following one-click installation script:

```bash
docker run -d \
  --name sqlbot \
  --restart unless-stopped \
  -p 8000:8000 \
  -p 8001:8001 \
  -v ./data/sqlbot/excel:/opt/sqlbot/data/excel \
  -v ./data/sqlbot/file:/opt/sqlbot/data/file \
  -v ./data/sqlbot/images:/opt/sqlbot/images \
  -v ./data/sqlbot/logs:/opt/sqlbot/app/logs \
  -v ./data/postgresql:/var/lib/postgresql/data \
  --privileged=true \
  dataease/sqlbot
```

You can also quickly deploy SQLBot through the [1Panel app store](https://apps.fit2cloud.com/1panel).

If you are in an intranet environment, you can deploy SQLBot via the [offline installation package](https://community.fit2cloud.com/#/products/sqlbot/downloads).


### Access methods

- Open in your browser: http://<your server IP>:8000/
- Username: admin
- Password: SQLBot@123456


## UI Display

  <tr>
    <img width="1920" height="991" alt="image" src="https://github.com/user-attachments/assets/c9f5e1ff-f654-4375-96be-5511fe30c120" />

    
  </tr>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dataease/sqlbot&type=Date)](https://www.star-history.com/#dataease/sqlbot&Date)

## Other star projects under FIT2CLOUD

- [DataEase](https://github.com/dataease/dataease/) - Open source BI tools
- [1Panel](https://github.com/1panel-dev/1panel/) - A modern, open-source Linux server operation and maintenance management panel
- [MaxKB](https://github.com/1panel-dev/MaxKB/) - Powerful and easy-to-use enterprise-grade intelligent agent platform
- [JumpServer](https://github.com/jumpserver/jumpserver/) - Popular open source bastion hosts
- [Cordys CRM](https://github.com/1Panel-dev/CordysCRM) - A new generation of open-source AI CRM systems
- [Halo](https://github.com/halo-dev/halo/) - Powerful and easy-to-use open-source website building tools
- [MeterSphere](https://github.com/metersphere/metersphere/) - Next-generation open-source continuous testing tools

## License

This repository is licensed under the [FIT2CLOUD Open Source License](LICENSE), which is essentially GPLv3 but with some additional restrictions.

You may conduct secondary development based on the SQLBot source code, but you must adhere to the following:

- You cannot replace or modify the SQLBot logo and copyright information;

- Derivative works resulting from secondary development must comply with the open-source obligations of GPL v3.

For commercial licensing, please contact support@fit2cloud.com.
