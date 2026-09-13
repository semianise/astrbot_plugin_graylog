"""
AstrBot 插件：连接 Graylog（方案 1 —— 直连 Graylog REST API）

本插件提供连接 Graylog 的基础能力：在 WebUI 配置面板填写 Graylog 地址与 Access Token，
即可建立带鉴权的 REST API 连接，作为后续功能（查询、统计等）扩展的底座。

配置：在 WebUI 插件配置面板填写 Graylog 地址 + Access Token（由 _conf_schema.json 定义，均需手动填写）
依赖：httpx（异步网络请求）
"""
import httpx

from astrbot.api.star import Context, Star, register


@register("astrbot_plugin_graylog", "semianise", "连接 Graylog：REST API 基础连接（配置地址 + Token）", "1.0.0")
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
