from typing import Optional

import httpx

from app.conf.app_config import EmbeddingConfig, app_config


class LocalTEIEmbeddingClient:
    """面向本地 TEI 服务的异步 Embedding 客户端。"""

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.base_url = f"http://{config.host}:{config.port}"
        self.client: Optional[httpx.AsyncClient] = None

    def init(self):
        """创建可复用的异步 HTTP 客户端。"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.config.timeout),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )

    async def close(self):
        """释放 HTTP 连接池。"""
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        """通过 TEI 原生接口批量生成向量。"""
        if not texts:
            return []
        if self.client is None:
            raise RuntimeError("Embedding client has not been initialized")
        if any(not isinstance(text, str) for text in texts):
            raise TypeError("TEI embedding inputs must be strings")

        response = await self.client.post(
            "/embed",
            json={"inputs": texts, "normalize": True},
        )
        if response.is_error:
            detail = response.text[:1000]
            raise RuntimeError(
                f"Embedding service returned HTTP {response.status_code}: {detail}"
            )

        payload = response.json()
        if not isinstance(payload, list) or len(payload) != len(texts):
            raise RuntimeError(
                "Embedding service returned an unexpected number of vectors: "
                f"expected {len(texts)}, got "
                f"{len(payload) if isinstance(payload, list) else type(payload).__name__}"
            )

        vectors: list[list[float]] = []
        for index, vector in enumerate(payload):
            if not isinstance(vector, list) or not vector:
                raise RuntimeError(f"Embedding vector at index {index} is invalid")
            if not all(isinstance(value, (int, float)) for value in vector):
                raise RuntimeError(f"Embedding vector at index {index} is not numeric")
            vectors.append([float(value) for value in vector])

        expected_dimension = app_config.qdrant.embedding_size
        invalid_dimensions = {
            len(vector) for vector in vectors if len(vector) != expected_dimension
        }
        if invalid_dimensions:
            raise RuntimeError(
                "Embedding dimension does not match Qdrant configuration: "
                f"expected {expected_dimension}, got {sorted(invalid_dimensions)}"
            )
        return vectors

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """为多条原始文本生成向量。"""
        return await self._embed(texts)

    async def aembed_query(self, text: str) -> list[float]:
        """为单条查询文本生成向量。"""
        vectors = await self._embed([text])
        return vectors[0]


class EmbeddingClientManager:
    """管理本地 TEI Embedding 客户端的生命周期。"""

    def __init__(self, config: EmbeddingConfig):
        self.client: Optional[LocalTEIEmbeddingClient] = None
        self.config = config

    def init(self):
        """初始化 Embedding 客户端。"""
        if self.client is None:
            self.client = LocalTEIEmbeddingClient(self.config)
            self.client.init()

    async def close(self):
        """关闭 Embedding 客户端。"""
        if self.client is not None:
            await self.client.close()


embedding_client_manager = EmbeddingClientManager(app_config.embedding)
