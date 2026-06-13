from abc import ABC, abstractmethod
from typing import Any


class BaseGraphReader(ABC):
    @abstractmethod
    def read(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError
