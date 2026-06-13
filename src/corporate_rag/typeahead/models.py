from typing import Any

from pydantic import BaseModel


class TypeaheadResponse(BaseModel):
    kind: str
    query: str
    items: list[dict[str, Any]]
    elapsed_ms: float
    cache_hit: bool
