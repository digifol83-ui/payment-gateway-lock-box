"""Agent response model."""
from enum import Enum
from typing import Any, Optional


class AgentStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class AgentResponse:
    def __init__(self, status: AgentStatus, result: Optional[dict] = None, error: Optional[str] = None):
        self.status = status
        self.result = result or {}
        self.error = error

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
        }
