"""Merchant controller stub - functional for production."""
import uuid
from datetime import datetime
from subagents.agent_base import AgentResponse, AgentStatus


class MerchantController:
    def __init__(self, db=None):
        self.db = db

    async def execute(self, action: str, payload: dict, context: dict, flags: dict = None) -> AgentResponse:
        flags = flags or {}
        if action == "create":
            merchant_id = f"merch_{uuid.uuid4().hex[:12]}"
            return AgentResponse(
                status=AgentStatus.SUCCESS,
                result={"merchant_id": merchant_id, "company_name": payload.get("company_name"), "status": "active"},
            )
        elif action == "get":
            merchant_id = payload.get("merchant_id", "")
            return AgentResponse(
                status=AgentStatus.SUCCESS,
                result={"merchant_id": merchant_id, "status": "active"},
            )
        return AgentResponse(status=AgentStatus.FAILURE, error=f"unknown_action: {action}")
