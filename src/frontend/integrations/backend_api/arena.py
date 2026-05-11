from typing import Any

from src.frontend.integrations.backend_api.base import BaseApiClient
from src.shared.schemas import CoreResponseDTO, StateTransitionDTO
from src.shared.schemas.arena import ArenaActionDTO, ArenaActionEnum, ArenaModeEnum, ArenaUIPayloadDTO

ArenaResponse = CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO | dict[str, Any]]


class BackendArenaApi(BaseApiClient):
    async def view(self, access_token: str, *, char_id: int) -> ArenaResponse:
        response = await self._request(
            "GET",
            f"/arena/v2/{char_id}/view",
            response_model=ArenaResponse,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return _normalize_arena_response(response)

    async def action(
        self,
        access_token: str,
        *,
        char_id: int,
        action: str,
        mode: str | None = None,
        value: dict[str, Any] | None = None,
    ) -> ArenaResponse:
        dto = ArenaActionDTO(action=action, mode=mode, value=value)
        method, path = self._action_route(char_id=char_id, action=action, mode=mode)
        if method == "GET":
            response = await self._request(
                "GET",
                path,
                response_model=ArenaResponse,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return _normalize_arena_response(response)
        response = await self._request(
            "POST",
            path,
            response_model=ArenaResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )
        return _normalize_arena_response(response)

    async def group_action(
        self,
        access_token: str,
        *,
        char_id: int,
        action: str,
        item_id: str | None = None,
    ) -> ArenaResponse:
        dto = ArenaActionDTO(
            action=action,
            mode=ArenaModeEnum.GROUP.value,
            value={"item_id": item_id} if item_id else None,
        )
        response = await self._request(
            "POST",
            f"/arena/v2/{char_id}/group/action",
            response_model=ArenaResponse,
            headers={"Authorization": f"Bearer {access_token}"},
            json=dto.model_dump(mode="json"),
        )
        return _normalize_arena_response(response)

    @staticmethod
    def _action_route(*, char_id: int, action: str, mode: str | None) -> tuple[str, str]:
        if action in {ArenaActionEnum.MENU_MAIN.value, ArenaActionEnum.LEAVE.value}:
            return "POST", f"/arena/v2/{char_id}/action"
        if action == ArenaActionEnum.MENU_MODE.value:
            if mode == ArenaModeEnum.GROUP.value:
                return "GET", f"/arena/v2/{char_id}/group/lobby"
            if mode == ArenaModeEnum.ONE_VS_ONE.value:
                return "GET", f"/arena/v2/{char_id}/duel/view"
            raise ValueError(f"Unsupported arena mode: {mode}")
        if action in {
            ArenaActionEnum.JOIN_QUEUE.value,
            ArenaActionEnum.START_SHADOW.value,
            ArenaActionEnum.CHECK_MATCH.value,
            ArenaActionEnum.ACCEPT_SHADOW.value,
            ArenaActionEnum.CONTINUE_SEARCH.value,
            ArenaActionEnum.CHECK_COMBAT_READY.value,
            ArenaActionEnum.CANCEL_QUEUE.value,
        }:
            return "POST", f"/arena/v2/{char_id}/duel/action"
        raise ValueError(f"Unsupported arena action: {action}")


def _normalize_arena_response(response: ArenaResponse) -> ArenaResponse:
    if isinstance(response.payload, dict) and response.payload_type != "state_transition":
        return response.model_copy(update={"payload": ArenaUIPayloadDTO.model_validate(response.payload)})
    return response
