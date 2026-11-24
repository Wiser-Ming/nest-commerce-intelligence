from typing import Annotated

from fastapi import Depends

from app.services.intent_service import IntentService, intent_service
from app.services.query_service import QueryService


async def get_intent_service() -> IntentService:
    return intent_service


async def get_query_service(
    classifier: Annotated[IntentService, Depends(get_intent_service)],
) -> QueryService:
    return QueryService(classifier)
