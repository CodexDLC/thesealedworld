from __future__ import annotations

from fastapi import Request

from fastapi_cabinet.messaging.bridge import MessagingActionResult, MessagingBridge


class MessagingWorkflowService:
    def __init__(self, bridge: MessagingBridge) -> None:
        self._bridge = bridge

    async def handle_registration_action(
        self,
        *,
        request: Request,
        request_id: str,
        action: str,
    ) -> MessagingActionResult:
        if action == "approve":
            return await self._bridge.approve_registration(request=request, request_id=request_id)
        if action == "deny":
            return await self._bridge.deny_registration(request=request, request_id=request_id)
        return MessagingActionResult(ok=False, code="unknown_action", message=f"Unknown action: {action!r}")


__all__ = ["MessagingWorkflowService"]
