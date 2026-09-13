# astrbot_plugin_graylog

让 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 通过 Graylog REST API 查询日志、做统计分析的插件（**只读**）。

## 功能

- **指令** `/graylog <关键字> [小时数]` —— 手动查询日志
- **指令** `/graylog_inputs` —— 列出所有 input
- **指令** `/graylog_top [关键字] [小时数]` —— 来源设备 Top N 统计
- **指令** `/graylog_trend [关键字] [小时数]` —— 日志量时间趋势
- **LLM 工具** `graylog_search` / `graylog_list_inputs` / `graylog_top_terms` / `graylog_trend` —— 让 agent 用自然语言查日志、做统计分析

查询返回：匹配条数 + 前 20 条日志（时间、来源、级别、内容）。

> **只读**：本插件不含任何写操作。增删改 input / stream 等请在 Graylog WebUI 自行操作。

## 环境要求

- AstrBot（使用 `@register` 与 `_conf_schema.json` 配置面板，建议 4.x）
- Graylog（6.x 实测），REST API 默认监听 `9000` 端口
- 一个 Graylog Access Token（只读权限即可）

## 安装

**方式一：zip 上传**

WebUI → 插件 → 安装插件 → 上传 zip。

**方式二：GitHub 链接**

WebUI → 插件 → 安装插件 → 粘贴本仓库地址。

## 配置

安装后到插件配置面板填写：

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `graylog_url` | Graylog 地址（不含 `/api`） | `http://<IP>:9000` |
| `graylog_token` | Access Token | 空 |

Token 创建：Graylog → System → Users and Teams → 用户 → More → Edit tokens → Create Token。

## 使用

```
/graylog error 1                 # 查近 1 小时含 error 的日志
/graylog "source:sw-core-01" 2   # 查近 2 小时来自 sw-core-01 的日志
/graylog "*" 24                  # 查近 24 小时全部日志
/graylog_inputs                  # 列出所有 input
/graylog_top error 24            # 过去 24 小时含 error 的日志，来源设备 Top N
/graylog_trend "*" 24            # 过去 24 小时日志量趋势
```

agent 模式下直接说「帮我查最近一小时有没有 error 日志」「哪台设备日志最多」「日志量最近有没有突增」，会自动调用对应工具。

## 技术说明

- 鉴权：Graylog Basic Auth，用户名 = token，密码 = 字面量 `token`
- 查询：`/api/search/universal/relative`（日志搜索）、`/terms`（Top N 统计）、`/histogram`（时间趋势）
- 查看：`/api/system/inputs`（列出 input）
- 全部为只读操作，无任何写接口
