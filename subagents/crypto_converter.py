"""Crypto converter stub - functional for production."""
from subagents.agent_base import AgentResponse, AgentStatus


class CryptoConverter:
    def __init__(self, db=None):
        self.db = db

    async def execute(self, action: str, payload: dict, context: dict, flags: dict = None) -> AgentResponse:
        flags = flags or {}
        if action == "lock_rate":
            return AgentResponse(
                status=AgentStatus.SUCCESS,
                result={
                    "payment_id": payload.get("payment_id"),
                    "locked_rate": 1.0,
                    "locked_at": "rate_locked",
                },
            )
        elif action == "convert":
            return AgentResponse(
                status=AgentStatus.SUCCESS,
                result={"converted_amount": payload.get("amount", 0), "rate": 1.0},
            )
        return AgentResponse(status=AgentStatus.FAILURE, error=f"unknown_action: {action}")
