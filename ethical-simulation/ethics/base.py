"""Interface implemented by future ethical decision strategies."""

from abc import ABC, abstractmethod
from typing import Any


class EthicalFramework(ABC):
    @abstractmethod
    def decide(self, state: dict[str, Any]) -> str | None:
        """Choose an action from a snapshot of environment state."""
        raise NotImplementedError
