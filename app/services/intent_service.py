from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import laya
import torch

from app.conf.app_config import app_config, project_root
from app.core.log import logger


class IntentService:
    """使用微调后的 Laya 决定请求是否进入 SQL Agent。"""

    def __init__(self) -> None:
        self._agent: Any | None = None
        self._lock = threading.Lock()

    @property
    def model_path(self) -> Path:
        configured = Path(app_config.intent_router.model_path)
        return configured if configured.is_absolute() else project_root / configured

    @property
    def device(self) -> str:
        requested = app_config.intent_router.device
        if requested == "cuda" and not torch.cuda.is_available():
            logger.warning("Laya 配置为 cuda，但当前进程不可用 CUDA，回退到 CPU")
            return "cpu"
        return requested

    def init(self) -> None:
        if self._agent is not None:
            return
        model_path = self.model_path
        if not model_path.exists():
            raise FileNotFoundError(f"Laya 微调模型不存在: {model_path}")
        self._agent = laya.load(str(model_path), device=self.device)
        logger.info(f"Laya 意图分类模型加载完成: model={model_path}, device={self.device}")

    def classify(self, query: str) -> dict[str, Any]:
        """返回意图、置信度和各候选概率。"""

        if self._agent is None:
            self.init()
        questions = {
            "intent": {
                "type": "choice",
                "instructions": "判断用户问题应该进入哪个处理分支。只有明确要求读取真实业务数据时才进入数据库查询。",
                "criteria": {
                    "database_query": "需要查询、统计、筛选、比较真实业务数据库中的销售、订单、商品、客户或库存数据",
                    "non_database": "不需要读取真实业务数据库，包括知识问答、技术问题、指标解释、闲聊、写作、翻译或越权写操作",
                    "clarification": "有潜在业务查询意图，但缺少时间范围、对象、指标或其他关键条件，需要先澄清",
                },
            }
        }
        with self._lock:
            result = self._agent.predict({"query": query}, questions)
        answer = result["answers"]["intent"]
        return {
            "intent": answer["choice"],
            "confidence": float(answer.get("confidence", 0.0)),
            "probabilities": answer.get("probabilities", {}),
            "model": "shopkeeper-router-head",
        }


intent_service = IntentService()
