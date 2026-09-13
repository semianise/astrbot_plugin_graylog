"""
AstrBot 插件：操控 Graylog（方案 1 —— 直连 Graylog REST API，只读）

功能：
  1. 指令  /graylog <关键字> [小时数]  —— 手动查日志
  2. LLM 工具 graylog_search          —— 让 agent 自然语言触发查日志
  3. 指令  /graylog_inputs            —— 列出所有 input
  4. 指令  /graylog_top [关键字] [小时数]  —— 来源设备 Top N 统计
  5. 指令  /graylog_trend [关键字] [小时数] —— 日志量时间趋势
  6. LLM 工具 graylog_list_inputs / graylog_top_terms / graylog_trend

只读：本插件不含任何写操作（增删改 input/stream 等请在 Graylog WebUI 自行操作）
配置：在 WebUI 插件配置面板填写 Graylog 地址 + Access Token（由 _conf_schema.json 定义，均需手动填写）
依赖：httpx（异步网络请求）
"""
import httpx

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageEventResult, filter
from astrbot.api.star import Context, Star, register


@register("astrbot_plugin_graylog", "semianise", "操控 Graylog：查询日志、统计分析（只读）", "1.3.1")
class GraylogPlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        # config 是 AstrBotConfig（dict 子类），由 _conf_schema.json 定义、WebUI 填写
        self.config = config

    def _get(self, key: str, default):
        """安全读取配置项，未填/缺失时回退到默认值。"""
        if self.config is None:
            return default
        val = self.config.get(key) if hasattr(self.config, "get") else None
        return val if val not in (None, "") else default

    def _creds(self):
        """取出配置里的地址和 token（均无默认值，需手动填写）。"""
        base_url = self._get("graylog_url", "")
        token = self._get("graylog_token", "")
        return base_url, token

    def _client(self, base_url: str, token: str) -> httpx.AsyncClient:
        """构造带 Graylog 鉴权的异步 HTTP 客户端。"""
        return httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/api",
            # Graylog 规定：Basic Auth，用户名 = token，密码 = 字面量 "token"
            auth=(token, "token"),
            headers={"Accept": "application/json", "X-Requested-By": "astrbot"},
            timeout=15.0,
        )

    async def _search(self, query: str, hours: float, limit: int = 20) -> str:
        """调 Graylog 相对时间搜索接口，返回人类可读文本。"""
        base_url, token = self._creds()
        if not base_url:
            return "Graylog 地址未配置：请在 WebUI 插件配置面板填 graylog_url。"
        if not token:
            return "Graylog Token 未配置：请在 WebUI 插件配置面板填 graylog_token。"

        params = {
            "query": query.strip() or "*",
            "range": int(hours * 3600),   # 相对时间搜索：往前多少秒
            "limit": limit,
            "fields": "timestamp,source,level,message",
            "sort": "timestamp:desc",
        }
        async with self._client(base_url, token) as client:
            try:
                resp = await client.get("/search/universal/relative", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Graylog 返回错误状态：{e}")
                return f"Graylog 请求失败（HTTP {e.response.status_code}）"
            except httpx.HTTPError as e:
                logger.error(f"Graylog 请求异常：{e}")
                return f"连不上 Graylog：{e}"

        total = data.get("total_results", 0)
        messages = data.get("messages", [])
        if not messages:
            return f"近 {hours} 小时没有匹配「{query}」的日志。"

        lines = [f"共 {total} 条，显示前 {len(messages)} 条："]
        for m in messages:
            f = m.get("message", {})
            ts = str(f.get("timestamp", ""))[:19]
            src = f.get("source", "?")
            lvl = f.get("level", "")
            text = str(f.get("message", "")).strip()
            if len(text) > 300:
                text = text[:300] + "..."
            lines.append(f"[{ts}] {src} {lvl} {text}".strip())
        return "\n".join(lines)

    async def _format_inputs(self) -> str:
        """列出 Graylog 所有 input，返回可读文本。"""
        base_url, token = self._creds()
        if not base_url:
            return "Graylog 地址未配置：请在 WebUI 插件配置面板填 graylog_url。"
        if not token:
            return "Graylog Token 未配置：请在 WebUI 插件配置面板填 graylog_token。"
        async with self._client(base_url, token) as client:
            try:
                resp = await client.get("/system/inputs")
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"列 input 失败：{e}")
                return f"Graylog 请求失败（HTTP {e.response.status_code}）"
            except httpx.HTTPError as e:
                logger.error(f"列 input 异常：{e}")
                return f"连不上 Graylog：{e}"

        inputs = data.get("inputs", [])
        if not inputs:
            return "当前没有任何 input。"
        lines = [f"共 {len(inputs)} 个 input："]
        for inp in inputs:
            attrs = inp.get("attributes") or {}
            port = attrs.get("port", "?")
            title = inp.get("title", "?")
            t = inp.get("type", "") or ""
            if "udp" in t.lower():
                kind = "syslog-udp"
            elif "tcp" in t.lower():
                kind = "syslog-tcp"
            else:
                kind = t.split(".")[-1] or "?"
            state = "运行中" if inp.get("node") else "未启动"
            lines.append(f"- {title}｜{kind}｜端口 {port}｜{state}｜id={str(inp.get('id', ''))[:8]}")
        return "\n".join(lines)

    async def _top_terms(self, field: str, query: str, hours: float, size: int = 10) -> str:
        """统计某字段出现次数最多的 Top N 值。"""
        base_url, token = self._creds()
        if not base_url:
            return "Graylog 地址未配置：请在 WebUI 插件配置面板填 graylog_url。"
        if not token:
            return "Graylog Token 未配置：请在 WebUI 插件配置面板填 graylog_token。"
        params = {
            "field": field,
            "query": query.strip() or "*",
            "range": int(hours * 3600),
            "size": size,
            "order": "desc",
        }
        async with self._client(base_url, token) as client:
            try:
                resp = await client.get("/search/universal/relative/terms", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"统计 Top 失败：{e}")
                return f"Graylog 请求失败（HTTP {e.response.status_code}）"
            except httpx.HTTPError as e:
                logger.error(f"统计 Top 异常：{e}")
                return f"连不上 Graylog：{e}"

        terms = (data.get("terms") or {}).get(field) or []
        if not terms:
            return f"近 {hours} 小时没有可统计的「{field}」数据。"
        lines = [f"近 {hours} 小时「{field}」Top {len(terms)}："]
        for i, t in enumerate(terms, 1):
            lines.append(f"{i}. {t.get('term', '?')}（{t.get('count', 0)} 条）")
        return "\n".join(lines)

    async def _trend(self, query: str, hours: float, interval: str = "") -> str:
        """日志量随时间变化的趋势（时间直方图）。"""
        base_url, token = self._creds()
        if not base_url:
            return "Graylog 地址未配置：请在 WebUI 插件配置面板填 graylog_url。"
        if not token:
            return "Graylog Token 未配置：请在 WebUI 插件配置面板填 graylog_token。"
        if not interval:
            interval = "minute" if hours < 1 else ("hour" if hours <= 72 else "day")
        params = {
            "query": query.strip() or "*",
            "range": int(hours * 3600),
            "interval": interval,
        }
        async with self._client(base_url, token) as client:
            try:
                resp = await client.get("/search/universal/relative/histogram", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"趋势统计失败：{e}")
                return f"Graylog 请求失败（HTTP {e.response.status_code}）"
            except httpx.HTTPError as e:
                logger.error(f"趋势统计异常：{e}")
                return f"连不上 Graylog：{e}"

        histogram = data.get("histogram") or []
        if not histogram:
            return f"近 {hours} 小时没有数据，无法画趋势。"
        max_count = max((int(b.get("count", 0)) for b in histogram), default=0) or 1
        lines = [f"日志量趋势（近 {hours} 小时，间隔 {interval}）："]
        for b in histogram:
            count = int(b.get("count", 0))
            t = str(b.get("time", "") or "")
            if "T" in t:
                t = t.split("T")[1][:5]
            bar = "█" * round(count / max_count * 16) if count else ""
            lines.append(f"{t} {bar} {count}")
        return "\n".join(lines)

    # ---- 指令：/graylog 关键字 [小时数] ----
    @filter.command("graylog")
    async def graylog_cmd(self, event: AstrMessageEvent, message: str = ""):
        """查询 Graylog 日志。用法：/graylog <关键字> [往前查的小时数]"""
        parts = (message or "").strip().split()
        if not parts:
            yield event.plain_result("用法：/graylog <关键字> [小时数]，例如 /graylog error 2")
            return
        query = parts[0]
        hours = 1.0
        if len(parts) >= 2:
            try:
                hours = float(parts[1])
            except ValueError:
                hours = 1.0
        yield event.plain_result(await self._search(query, hours))

    # ---- 指令：/graylog_inputs 列 input ----
    @filter.command("graylog_inputs")
    async def graylog_inputs_cmd(self, event: AstrMessageEvent):
        """列出 Graylog 的所有 input（日志输入源）"""
        yield event.plain_result(await self._format_inputs())

    # ---- 指令：/graylog_top [关键字] [小时数] ----
    @filter.command("graylog_top")
    async def graylog_top_cmd(self, event: AstrMessageEvent, message: str = ""):
        """来源设备 Top N 统计。用法：/graylog_top [关键字] [小时数]，默认近 24 小时全部"""
        parts = (message or "").strip().split()
        query = parts[0] if parts else "*"
        hours = 24.0
        if len(parts) >= 2:
            try:
                hours = float(parts[1])
            except ValueError:
                hours = 24.0
        yield event.plain_result(await self._top_terms("source", query, hours))

    # ---- 指令：/graylog_trend [关键字] [小时数] ----
    @filter.command("graylog_trend")
    async def graylog_trend_cmd(self, event: AstrMessageEvent, message: str = ""):
        """日志量时间趋势。用法：/graylog_trend [关键字] [小时数]，默认近 24 小时全部"""
        parts = (message or "").strip().split()
        query = parts[0] if parts else "*"
        hours = 24.0
        if len(parts) >= 2:
            try:
                hours = float(parts[1])
            except ValueError:
                hours = 24.0
        yield event.plain_result(await self._trend(query, hours))

    # ---- LLM 工具：agent 自然语言触发 ----
    @filter.llm_tool(name="graylog_search")
    async def graylog_search(self, event: AstrMessageEvent, query: str, hours: float = 1) -> MessageEventResult:
        """在 Graylog 中搜索日志。
        Args:
            query(string): 搜索关键字或 Lucene 查询，如 "error"、'source:sw-core-01'；查全部填 "*"
            hours(number): 往前查询的小时数，默认 1
        """
        yield event.plain_result(await self._search(query, hours))

    @filter.llm_tool(name="graylog_list_inputs")
    async def graylog_list_inputs(self, event: AstrMessageEvent) -> MessageEventResult:
        """列出 Graylog 当前所有的 input（日志输入源）。
        """
        yield event.plain_result(await self._format_inputs())

    @filter.llm_tool(name="graylog_top_terms")
    async def graylog_top_terms(self, event: AstrMessageEvent, field: str = "source", query: str = "*", hours: float = 24, size: int = 10) -> MessageEventResult:
        """统计某字段出现次数最多的 Top N 值（默认统计来源 source，即哪台设备日志最多）。
        Args:
            field(string): 要统计的字段，默认 "source"（来源设备），也可以是 "level"（级别）等
            query(string): 过滤关键字或 Lucene 查询，默认 "*" 表示全部
            hours(number): 往前统计的小时数，默认 24
            size(number): 返回前几名，默认 10
        """
        yield event.plain_result(await self._top_terms(field, query, hours, size))

    @filter.llm_tool(name="graylog_trend")
    async def graylog_trend(self, event: AstrMessageEvent, query: str = "*", hours: float = 24, interval: str = "") -> MessageEventResult:
        """日志量随时间变化的趋势（时间直方图）。
        Args:
            query(string): 过滤关键字或 Lucene 查询，默认 "*" 表示全部
            hours(number): 往前统计的小时数，默认 24
            interval(string): 时间粒度，可填 minute / hour / day，留空自动选择
        """
        yield event.plain_result(await self._trend(query, hours, interval))
