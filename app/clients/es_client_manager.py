from typing import Optional

from elasticsearch import AsyncElasticsearch

from app.conf.app_config import ESConfig, app_config


class ESClientManager:
    """管理 Elasticsearch 客户端的生命周期"""

    def __init__(self, es_config: ESConfig):
        self.es_config = es_config
        self.client: Optional[AsyncElasticsearch] = None

    def _get_url(self) -> str:
        """拼接 Elasticsearch 服务地址"""
        return f"http://{self.es_config.host}:{self.es_config.port}"

    def init(self):
        """
        初始化异步 Elasticsearch 客户端
        hosts 之所以是列表，是为了兼容 ES 常见的集群连接方式
        """
        self.client = AsyncElasticsearch(hosts=[self._get_url()])

    async def close(self):
        """关闭客户端连接"""
        await self.client.close()


es_client_manager = ESClientManager(app_config.es)
