from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.core.log import logger
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.services.intent_service import IntentService


def sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


class QueryService:
    """编排意图路由和数据库查询流程。"""

    def __init__(self, intent_service: IntentService):
        self.intent_service = intent_service

    async def query(self, query: str) -> AsyncIterator[str]:
        """执行路由；非数据库请求在这里结束，不进入 SQL 图。"""

        yield sse({"type": "progress", "step": "识别问题类型", "status": "running"})
        try:
            route = await asyncio.to_thread(self.intent_service.classify, query)
            yield sse({"type": "route", **route})
            yield sse({"type": "progress", "step": "识别问题类型", "status": "success"})

            intent = route["intent"]
            if intent == "database_query":
                async for event in self._database_query(query):
                    yield event
            elif intent == "clarification":
                yield sse({
                    "type": "text",
                    "content": "这个问题可能需要查询业务数据，但信息还不完整。请补充时间范围、查询对象或指标名称。",
                })
            else:
                yield sse({
                    "type": "text",
                    "content": "这个问题无需访问业务数据库。本系统可以按时间、地区、品类或会员等级查询销售和订单数据。",
                })
            yield sse({"type": "done", "intent": intent})
        except Exception as error:
            logger.exception(f"查询入口执行失败: {error}")
            yield sse({"type": "error", "message": str(error)})

    async def _database_query(self, query: str) -> AsyncIterator[str]:
        """仅在确认数据库意图后创建数据库 Session 和检索仓储。"""

        async with (
            meta_mysql_client_manager.session_factory() as meta_session,
            dw_mysql_client_manager.session_factory() as dw_session,
        ):
            context = DataAgentContext(
                column_qdrant_repository=ColumnQdrantRepository(qdrant_client_manager.client),
                embedding_client=embedding_client_manager.client,
                metric_qdrant_repository=MetricQdrantRepository(qdrant_client_manager.client),
                value_es_repository=ValueESRepository(es_client_manager.client),
                meta_mysql_repository=MetaMySQLRepository(meta_session),
                dw_mysql_repository=DWMySQLRepository(dw_session),
            )
            state = DataAgentState(query=query)
            async for chunk in graph.astream(input=state, context=context, stream_mode="custom"):
                yield sse(chunk)
