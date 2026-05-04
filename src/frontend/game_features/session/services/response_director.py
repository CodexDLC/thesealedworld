from typing import Any

from fastapi import Request

from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO


class ResponseDirector:
    def __init__(self, *, context_builder: SessionContextBuilder) -> None:
        self.context_builder = context_builder

    async def resolve(
        self,
        request: Request,
        response: CoreResponseDTO[Any],
        *,
        source_state: CoreDomain,
        char_id: int,
        redirect_transitions: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        target_state = response.header.current_state
        if response.payload_type == "state_transition" or target_state != source_state:
            if redirect_transitions:
                return "__session_redirect__", {"char_id": char_id}
            context = await self.context_builder.build(
                request,
                state=target_state,
                char_id=char_id,
                quest_key=getattr(response.payload, "quest_key", None),
            )
            return "game/session_content.html", context

        if target_state == CoreDomain.EXPLORATION:
            return await self._resolve_exploration(request, response, char_id)
        if target_state == CoreDomain.ARENA:
            return self._resolve_arena(response, char_id)
        if target_state == CoreDomain.SCENARIO:
            context = await self.context_builder.build_from_response(request, response, char_id=char_id)
            context["oob_panels"] = True
            return "game/domains/scenario/viewport/main.html", context

        return "game/session.html", {
            "domain": target_state,
            "char_id": char_id,
            "payload": response.payload,
            "payload_type": response.payload_type,
        }

    async def _resolve_exploration(
        self,
        request: Request,
        response: CoreResponseDTO[Any],
        char_id: int,
    ) -> tuple[str, dict[str, Any]]:
        context = await self.context_builder.build_exploration_response(request, response, char_id=char_id)
        context["oob_panels"] = True
        return "game/domains/exploration/viewport/main.html", context

    def _resolve_arena(
        self,
        response: CoreResponseDTO[Any],
        char_id: int,
    ) -> tuple[str, dict[str, Any]]:
        return "game/domains/arena/viewport/main.html", {
            "domain": CoreDomain.ARENA,
            "char_id": char_id,
            "arena": response.payload,
            "payload_type": response.payload_type,
        }
