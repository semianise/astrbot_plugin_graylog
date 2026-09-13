# 更新日志

本项目的所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [1.3.1] - 2026-09-13

### 变更
- 安全：`graylog_url` 不再预填默认地址，改为安装后手动填写（与 token 一致，避免在插件里暴露实际地址）

## [1.3.0] - 2026-09-13

### 移除
- 移除写操作：删除「创建 syslog input」的指令 `/graylog_input` 与 LLM 工具 `graylog_create_input`
- 插件改为纯只读，增删改请在 Graylog WebUI 自行操作

## [1.2.0] - 2026-09-13

### 新增
- 统计分析：新增指令 `/graylog_top`（来源设备 Top N）与 LLM 工具 `graylog_top_terms`
- 时间趋势：新增指令 `/graylog_trend`（日志量趋势）与 LLM 工具 `graylog_trend`

## [1.1.0] - 2026-09-13

### 新增
- input 管理：新增指令 `/graylog_inputs`（列出 input）与 LLM 工具 `graylog_list_inputs`
- 新增指令 `/graylog_input <udp|tcp> [端口]` 与 LLM 工具 `graylog_create_input`（创建 syslog input，含查重）

## [1.0.0] - 2026-09-13

### 新增
- 初始版本：直连 Graylog REST API
- 指令 `/graylog <关键字> [小时数]` 查日志
- LLM 工具 `graylog_search` 让 agent 自然语言查日志
- 配置面板 `_conf_schema.json`（Graylog 地址 + Access Token）
