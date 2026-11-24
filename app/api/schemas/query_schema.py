from typing import Annotated

from pydantic import BaseModel, StringConstraints


class QuerySchema(BaseModel):
    """`/api/query` 请求体，承载用户输入的自然语言问题"""

    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
