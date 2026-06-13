from typing import Any

from pydantic import BaseModel


class FacetResponse(BaseModel):
    values: list[dict[str, Any]]
