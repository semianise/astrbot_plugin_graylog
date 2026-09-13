# astrbot_plugin_graylog

让 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 通过 Graylog REST API 连接 Graylog 的基础插件。

## 当前状态

- 提供连接 Graylog 的基础能力：配置 Graylog 地址与 Access Token，建立带鉴权的 REST API 连接
- 暂无对外功能（指令 / LLM 工具）；连接配置好即可作为后续功能开发的底座

## 环境要求

- AstrBot（使用 `@register` 与 `_conf_schema.json` 配置面板，建议 4.x）
- Graylog（REST API 默认监听 `9000` 端口）
- 一个 Graylog Access Token

## 安装

**方式一：zip 上传**

WebUI → 插件 → 安装插件 → 上传 zip。

**方式二：GitHub 链接**

WebUI → 插件 → 安装插件 → 粘贴本仓库地址。

## 配置

安装后到插件配置面板填写：

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `graylog_url` | Graylog 地址（不含 `/api`） | 空（手动填写） |
| `graylog_token` | Access Token | 空（手动填写） |

Token 创建：Graylog → System → Users and Teams → 用户 → More → Edit tokens → Create Token。

## 技术说明

- 鉴权：Graylog Basic Auth，用户名 = token，密码 = 字面量 `token`
- 连接：`httpx` 异步客户端，`base_url` 自动拼接 `/api`
