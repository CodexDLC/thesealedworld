from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, status
from loguru import logger

from src.frontend.config.settings import settings
from src.frontend.game_features.combat.view_models.screen import (
    build_combat_outcome_screen_from_dashboard_vm,
    build_combat_outcome_screen_from_result_vm,
    build_combat_result_screen_vm,
    build_combat_screen_from_result_vm,
    build_combat_screen_vm,
)
from src.frontend.game_features.inventory.view_models.window import build_inventory_window_vm
from src.frontend.game_features.session.token_state import require_game_access_token
from src.frontend.game_features.session.view_models.nav import build_game_nav
from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, EnterCharacterRequestDTO
from src.shared.schemas.arena import ArenaUIPayloadDTO
from src.shared.schemas.city_services import CityServiceUIPayloadDTO
from src.shared.schemas.exploration import EncounterDTO, ExplorationScreenDTO, WorldNavigationDTO
from src.shared.schemas.loot import LootClaimRequestDTO

if TYPE_CHECKING:
    from src.frontend.integrations.backend_api.arena import BackendArenaApi
    from src.frontend.integrations.backend_api.character_status import BackendCharacterStatusApi
    from src.frontend.integrations.backend_api.city_services import BackendCityServicesApi
    from src.frontend.integrations.backend_api.combat import BackendCombatApi
    from src.frontend.integrations.backend_api.exploration import BackendExplorationApi
    from src.frontend.integrations.backend_api.game_session import BackendGameSessionApi
    from src.frontend.integrations.backend_api.inventory import BackendInventoryApi
    from src.frontend.integrations.backend_api.rift import BackendRiftApi
    from src.frontend.integrations.backend_api.scenario import BackendScenarioApi
    from src.shared.schemas.character_status import CharacterActorCoreDTO
    from src.shared.schemas.combat import CombatDashboardDTO, CombatResultDTO
    from src.shared.schemas.inventory import InventoryWindowDTO


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 2)


def _realtime_ws_endpoint(raw_url: str) -> str:
    base = raw_url.rstrip("/")
    if base.endswith("/ws/realtime"):
        return base
    return f"{base}/ws/realtime"


def _log_session_timing(step: str, *, started_at: float, char_id: int, **extra: Any) -> None:
    logger.bind(step=step, char_id=char_id, duration_ms=_elapsed_ms(started_at), **extra).debug("FrontendSessionTiming")


class SessionContextBuilder:
    def __init__(
        self,
        *,
        character_status_api: BackendCharacterStatusApi,
        arena_api: BackendArenaApi,
        city_services_api: BackendCityServicesApi,
        exploration_api: BackendExplorationApi,
        scenario_api: BackendScenarioApi,
        game_session_api: BackendGameSessionApi,
        inventory_api: BackendInventoryApi,
        combat_api: BackendCombatApi | None = None,
        rift_api: BackendRiftApi | None = None,
    ) -> None:
        self.character_status_api = character_status_api
        self.arena_api = arena_api
        self.city_services_api = city_services_api
        self.combat_api = combat_api
        self.exploration_api = exploration_api
        self.scenario_api = scenario_api
        self.game_session_api = game_session_api
        self.inventory_api = inventory_api
        self.rift_api = rift_api

    async def build_current(self, request: Request, *, char_id: int) -> dict[str, Any]:
        token = require_game_access_token(request)
        started_at = perf_counter()
        response = await self.game_session_api.enter(token, EnterCharacterRequestDTO(character_id=char_id))
        _log_session_timing(
            "game_session_enter",
            started_at=started_at,
            char_id=char_id,
            state=response.header.current_state,
            payload_type=response.payload_type,
        )
        started_at = perf_counter()
        context = await self.build_from_response(request, response, char_id=char_id)
        _log_session_timing(
            "build_current_total_after_enter",
            started_at=started_at,
            char_id=char_id,
            domain=context.get("domain"),
        )
        return context

    async def build_state(
        self,
        request: Request,
        *,
        state: CoreDomain,
        char_id: int,
        quest_key: str | None = None,
        transition_context: dict[str, Any] | None = None,
        transition_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = require_game_access_token(request)

        if state == CoreDomain.SCENARIO:
            return_context = _return_context_from_transition(transition_context)
            npc_key = _transition_value("npc_key", transition_context, transition_metadata)
            scenario_response = (
                await self.scenario_api.initialize(
                    token,
                    char_id=char_id,
                    quest_key=quest_key,
                    npc_key=npc_key,
                    return_context=return_context,
                )
                if quest_key
                else await self.scenario_api.resume(token, char_id=char_id)
            )
            return await self.build_from_response(request, scenario_response, char_id=char_id)

        if state == CoreDomain.EXPLORATION:
            character_status = await self._character_status(token, char_id=char_id)
            status_payload = self._status_seed(character_status)
            initial_inventory_open, inventory_window = await self._inventory_window_state(
                token,
                char_id=char_id,
                character_status=character_status,
                status_payload=status_payload,
            )
            exploration_response = await self.exploration_api.look_around(token, char_id=char_id)
            if exploration_response.payload is None:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY, detail="Exploration payload is unavailable"
                )
            exploration_payload = exploration_response.payload
            exploration_payload, encounter_payload = self._split_exploration_payload(
                exploration_payload,
                payload_type=exploration_response.payload_type,
            )
            exploration_local_map = await self.exploration_api.local_map(token, char_id=char_id)
            return self._context(
                state=exploration_response.header.current_state,
                char_id=char_id,
                transaction_id=exploration_response.header.transaction_id,
                payload_type=exploration_response.payload_type,
                character_status=character_status,
                exploration=exploration_payload,
                encounter=encounter_payload,
                exploration_local_map=exploration_local_map,
                world_theme=getattr(exploration_payload, "world_theme", None)
                or getattr(character_status, "world_theme", None),
                status_seed=status_payload,
                inventory_window=inventory_window,
                initial_inventory_open=initial_inventory_open,
            )

        if state == CoreDomain.CITY_SERVICES:
            service_screen = _city_service_screen_from_transition(transition_context, transition_metadata)
            city_service_response = await self.city_services_api.view(
                token,
                char_id=char_id,
                screen=service_screen,
                service_id=_transition_value("service_id", transition_context, transition_metadata),
                section_id=_city_service_section_from_transition(transition_context, transition_metadata),
                tavern_id=_transition_value("tavern_id", transition_context, transition_metadata),
                location_id=_transition_value("location_id", transition_context, transition_metadata),
            )
            if city_service_response.payload is None:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="City service payload is unavailable",
                )
            city_service_payload = CityServiceUIPayloadDTO.model_validate(city_service_response.payload)
            character_status = await self._character_status(token, char_id=char_id)
            status_payload = self._status_seed(character_status)
            initial_inventory_open, inventory_window = await self._inventory_window_state(
                token,
                char_id=char_id,
                character_status=character_status,
                status_payload=status_payload,
            )
            return self._context(
                state=city_service_response.header.current_state,
                char_id=char_id,
                transaction_id=city_service_response.header.transaction_id,
                payload_type=city_service_response.payload_type,
                character_status=character_status,
                city_service=city_service_payload,
                background_url=city_service_payload.background_url,
                world_theme=getattr(character_status, "world_theme", None),
                status_seed=status_payload,
                inventory_window=inventory_window,
                initial_inventory_open=initial_inventory_open,
            )

        if state == CoreDomain.ARENA:
            arena_response = await self.arena_api.view(token, char_id=char_id)
            if arena_response.payload is None:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Arena payload is unavailable")
            arena_payload = ArenaUIPayloadDTO.model_validate(arena_response.payload)
            character_status = await self._character_status(token, char_id=char_id)
            status_payload = self._status_seed(character_status)
            initial_inventory_open, inventory_window = await self._inventory_window_state(
                token,
                char_id=char_id,
                character_status=character_status,
                status_payload=status_payload,
            )
            return self._context(
                state=arena_response.header.current_state,
                char_id=char_id,
                transaction_id=arena_response.header.transaction_id,
                payload_type=arena_response.payload_type,
                character_status=character_status,
                arena=arena_payload,
                background_url="/static/images/scenes/forest.webp",
                world_theme=getattr(character_status, "world_theme", None),
                status_seed=status_payload,
                inventory_window=inventory_window,
                initial_inventory_open=initial_inventory_open,
            )

        if state == CoreDomain.RIFT:
            if self.rift_api is None:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Rift API client is unavailable")
            character_status = await self._character_status(token, char_id=char_id)
            status_payload = self._status_seed(character_status)
            initial_inventory_open, inventory_window = await self._inventory_window_state(
                token,
                char_id=char_id,
                character_status=character_status,
                status_payload=status_payload,
            )
            rift_payload = await self.rift_api.view(token, char_id=char_id)
            if not rift_payload:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Rift payload is unavailable")
            return self._context(
                state=CoreDomain.RIFT,
                char_id=char_id,
                transaction_id="",
                payload_type="rift_screen",
                character_status=character_status,
                rift=rift_payload,
                background_url="/static/images/exploration/city/d4/52_52_runic_circle_plaza.webp",
                world_theme=getattr(character_status, "world_theme", None),
                status_seed=status_payload,
                inventory_window=inventory_window,
                initial_inventory_open=initial_inventory_open,
                game_state_scripts=["/static/js/game/states/rift.js"],
            )

        if state in {CoreDomain.COMBAT, CoreDomain.COMBAT_RESULT}:
            if self.combat_api is None:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Combat API client is unavailable")
            started_at = perf_counter()
            combat_response = await self.combat_api.view(token, char_id=char_id)
            _log_session_timing(
                "combat_view",
                started_at=started_at,
                char_id=char_id,
                payload_type=combat_response.payload_type,
            )
            combat_payload = combat_response.payload
            if combat_payload is None:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Combat payload is unavailable")

            if combat_response.payload_type == "state_transition":
                return await self.build_from_response(request, combat_response, char_id=char_id)

            # Type narrowing for Mypy
            from src.shared.schemas.combat import CombatDashboardDTO, CombatResultDTO

            if isinstance(combat_payload, CombatResultDTO):
                return self._context(
                    state=combat_response.header.current_state,
                    char_id=char_id,
                    transaction_id=combat_response.header.transaction_id,
                    payload_type=combat_response.payload_type,
                    combat_result=combat_payload,
                    combat_result_screen=build_combat_result_screen_vm(combat_payload),
                    combat_screen=build_combat_screen_from_result_vm(combat_payload),
                    combat_outcome_screen=build_combat_outcome_screen_from_result_vm(combat_payload),
                    background_url="/static/images/scenes/ruins.webp",
                    status_seed=self._empty_combat_status_seed(char_id),
                )

            if not isinstance(combat_payload, CombatDashboardDTO):
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid combat payload type")

            return self._context(
                state=combat_response.header.current_state,
                char_id=char_id,
                transaction_id=combat_response.header.transaction_id,
                payload_type=combat_response.payload_type,
                combat=combat_payload,
                combat_screen=build_combat_screen_vm(combat_payload),
                combat_outcome_screen=build_combat_outcome_screen_from_dashboard_vm(combat_payload),
                background_url="/static/images/scenes/ruins.webp",
                status_seed=self._combat_status_seed(combat_payload),
            )

        if state == CoreDomain.DEATH:
            character_status = await self._character_status(token, char_id=char_id)
            status_payload = self._status_seed(character_status)
            sessions = getattr(character_status, "sessions", {}) or {}
            post_combat = _post_combat_from_sources(transition_metadata, sessions)
            return self._context(
                state=CoreDomain.DEATH,
                char_id=char_id,
                transaction_id="",
                payload_type="death_session",
                character_status=character_status,
                background_url="/static/images/scenes/ruins.webp",
                world_theme=getattr(character_status, "world_theme", None),
                status_seed=status_payload,
                death={
                    "char_id": char_id,
                    "run_id": sessions.get("death_run_id") if isinstance(sessions, dict) else None,
                    "corpse_id": sessions.get("death_corpse_id") if isinstance(sessions, dict) else None,
                    "respawn_action": "/game/death/respawn",
                    "post_combat": post_combat,
                    "death_summary": (post_combat or {}).get("death_summary", {}),
                },
                initial_inventory_open=False,
            )

        if state == CoreDomain.LOOT:
            character_status = await self._character_status(token, char_id=char_id)
            status_payload = self._status_seed(character_status)
            sessions = getattr(character_status, "sessions", {}) or {}
            post_combat = _post_combat_from_sources(transition_metadata, sessions) or {}
            return self._context(
                state=CoreDomain.LOOT,
                char_id=char_id,
                transaction_id="",
                payload_type="loot_session",
                character_status=character_status,
                background_url="/static/images/scenes/ruins.webp",
                world_theme=getattr(character_status, "world_theme", None),
                status_seed=status_payload,
                loot={
                    "char_id": char_id,
                    "claim_action": "/game/loot/claim-all",
                    "post_combat": post_combat,
                    "notice": post_combat.get("notice"),
                    "corpse_ids": post_combat.get("corpse_ids") or [],
                    "loot_context": post_combat.get("loot_context") or {},
                },
                initial_inventory_open=False,
            )

        logger.bind(state=state, char_id=char_id).warning("SessionStateUnsupported")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=f"{state} screen is not implemented yet"
        )

    async def build_from_response(
        self,
        request: Request,
        response: CoreResponseDTO[Any],
        *,
        char_id: int,
    ) -> dict[str, Any]:
        state = response.header.current_state
        if not isinstance(state, CoreDomain):
            state = CoreDomain(str(state))

        if state == CoreDomain.LOBBY:
            raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/game-lobby"})

        if response.payload_type == "state_transition" or state != CoreDomain.SCENARIO:
            quest_key = _payload_value(response.payload, "quest_key")
            return await self.build_state(
                request,
                state=state,
                char_id=char_id,
                quest_key=quest_key,
                transition_context=_payload_value(response.payload, "context"),
                transition_metadata=_payload_value(response.payload, "metadata"),
            )

        if response.payload_type != "scenario_screen":
            return await self.build_state(request, state=state, char_id=char_id)

        if response.payload is None or not hasattr(response.payload, "node_key"):
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Scenario payload is unavailable")

        token = require_game_access_token(request)
        character_status = await self._character_status(token, char_id=char_id)
        status_payload = self._status_seed(character_status)
        extra_data = getattr(response.payload, "extra_data", None) or {}
        response.payload.extra_data = {
            **extra_data,
            "char_id": char_id,
            "quest_key": extra_data.get("quest_key", "awakening_rift"),
        }
        return self._context(
            state=state,
            char_id=char_id,
            transaction_id=response.header.transaction_id,
            payload_type=response.payload_type,
            character_status=character_status,
            scenario=response.payload,
            background_url=response.payload.extra_data.get("background_url"),
            world_theme=getattr(character_status, "world_theme", None),
            status_seed=status_payload,
            initial_inventory_open=False,
        )

    async def respawn(self, request: Request, *, char_id: int) -> dict[str, Any]:
        token = require_game_access_token(request)
        response = await self.game_session_api.respawn(token, EnterCharacterRequestDTO(character_id=char_id))
        return await self.build_from_response(request, response, char_id=char_id)

    async def claim_loot(self, request: Request, *, char_id: int, corpse_ids: list[str]) -> dict[str, Any]:
        token = require_game_access_token(request)
        response = await self.game_session_api.claim_loot(
            token,
            LootClaimRequestDTO(char_id=char_id, corpse_ids=corpse_ids),
        )
        return await self.build_from_response(request, response, char_id=char_id)

    async def build_exploration_response(
        self,
        request: Request,
        response: CoreResponseDTO[Any],
        *,
        char_id: int,
    ) -> dict[str, Any]:
        if response.payload is None:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Exploration payload is unavailable")

        token = require_game_access_token(request)
        character_status = await self._character_status(token, char_id=char_id)
        status_payload = self._status_seed(character_status)
        initial_inventory_open, inventory_window = await self._inventory_window_state(
            token,
            char_id=char_id,
            character_status=character_status,
            status_payload=status_payload,
        )
        exploration_payload = response.payload
        exploration_payload, encounter_payload = self._split_exploration_payload(
            exploration_payload,
            payload_type=response.payload_type,
        )
        if encounter_payload is not None and not isinstance(exploration_payload, WorldNavigationDTO):
            metadata_navigation = self._navigation_from_encounter(encounter_payload)
            if metadata_navigation is not None:
                exploration_payload = metadata_navigation
            else:
                navigation_response = await self.exploration_api.look_around(token, char_id=char_id)
                if isinstance(navigation_response.payload, WorldNavigationDTO):
                    exploration_payload = navigation_response.payload
                elif navigation_response.payload_type == "exploration_encounter" or isinstance(
                    navigation_response.payload, EncounterDTO
                ):
                    navigation_encounter = EncounterDTO.model_validate(navigation_response.payload)
                    navigation_payload = self._navigation_from_encounter(navigation_encounter)
                    if navigation_payload is not None:
                        exploration_payload = navigation_payload

        exploration_local_map = await self.exploration_api.local_map(token, char_id=char_id)
        return self._context(
            state=response.header.current_state,
            char_id=char_id,
            transaction_id=response.header.transaction_id,
            payload_type=response.payload_type,
            character_status=character_status,
            exploration=exploration_payload,
            encounter=encounter_payload,
            exploration_local_map=exploration_local_map,
            world_theme=getattr(exploration_payload, "world_theme", None)
            or getattr(character_status, "world_theme", None),
            status_seed=status_payload,
            inventory_window=inventory_window,
            initial_inventory_open=initial_inventory_open,
        )

    def _split_exploration_payload(
        self,
        payload: Any,
        *,
        payload_type: str | None,
    ) -> tuple[Any, EncounterDTO | None]:
        if isinstance(payload, ExplorationScreenDTO) or (
            isinstance(payload, dict) and isinstance(payload.get("content"), dict) and "context" in payload
        ):
            screen = ExplorationScreenDTO.model_validate(payload)
            content = screen.content.data
            if screen.content.kind == "encounter" or payload_type == "exploration_encounter":
                encounter = EncounterDTO.model_validate(content)
                return self._navigation_from_encounter(encounter) or content, encounter
            if screen.content.kind == "navigation":
                return WorldNavigationDTO.model_validate(content), None
            return content, None

        if payload_type == "exploration_encounter" or isinstance(payload, EncounterDTO):
            encounter = EncounterDTO.model_validate(payload)
            return self._navigation_from_encounter(encounter) or payload, encounter
        return payload, None

    @staticmethod
    def _navigation_from_encounter(encounter: EncounterDTO) -> WorldNavigationDTO | None:
        metadata = encounter.metadata if isinstance(encounter.metadata, dict) else {}
        raw_navigation = metadata.get("navigation")
        if not isinstance(raw_navigation, dict):
            return None
        try:
            return WorldNavigationDTO.model_validate(raw_navigation)
        except Exception:  # noqa: BLE001
            return None

    async def build(
        self,
        request: Request,
        *,
        state: CoreDomain,
        char_id: int,
        quest_key: str | None = None,
        transition_context: dict[str, Any] | None = None,
        transition_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.build_state(
            request,
            state=state,
            char_id=char_id,
            quest_key=quest_key,
            transition_context=transition_context,
            transition_metadata=transition_metadata,
        )

    def build_combat_dashboard_context(
        self,
        dashboard: CombatDashboardDTO,
        *,
        char_id: int,
        transaction_id: str = "",
        payload_type: str = "CombatDashboard",
    ) -> dict[str, Any]:
        return self._context(
            state=CoreDomain.COMBAT,
            char_id=char_id,
            transaction_id=transaction_id,
            payload_type=payload_type,
            combat=dashboard,
            combat_screen=build_combat_screen_vm(dashboard),
            combat_outcome_screen=build_combat_outcome_screen_from_dashboard_vm(dashboard),
            background_url="/static/images/scenes/ruins.webp",
            status_seed=self._combat_status_seed(dashboard),
        )

    def build_combat_result_context(
        self,
        result: CombatResultDTO,
        *,
        char_id: int,
        transaction_id: str = "",
        payload_type: str = "CombatResult",
    ) -> dict[str, Any]:
        return self._context(
            state=CoreDomain.COMBAT,
            char_id=char_id,
            transaction_id=transaction_id,
            payload_type=payload_type,
            combat_result=result,
            combat_result_screen=build_combat_result_screen_vm(result),
            combat_screen=build_combat_screen_from_result_vm(result),
            combat_outcome_screen=build_combat_outcome_screen_from_result_vm(result),
            background_url="/static/images/scenes/ruins.webp",
            status_seed=self._empty_combat_status_seed(char_id),
        )

    async def _character_status(self, token: str, *, char_id: int) -> CharacterActorCoreDTO:
        return await self.character_status_api.get_panel(token, char_id=char_id)

    def _context(
        self,
        *,
        state: CoreDomain | str,
        char_id: int,
        transaction_id: str,
        payload_type: str | None,
        character_status: CharacterActorCoreDTO | None = None,
        scenario: Any | None = None,
        exploration: Any | None = None,
        exploration_local_map: Any | None = None,
        encounter: Any | None = None,
        arena: Any | None = None,
        city_service: Any | None = None,
        combat: Any | None = None,
        combat_screen: Any | None = None,
        combat_result: Any | None = None,
        combat_result_screen: Any | None = None,
        combat_outcome_screen: Any | None = None,
        death: dict[str, Any] | None = None,
        loot: dict[str, Any] | None = None,
        rift: dict[str, Any] | None = None,
        background_url: str | None = None,
        world_theme: Any | None = None,
        status_seed: dict[str, Any] | None = None,
        inventory_window: InventoryWindowDTO | Any | None = None,
        initial_inventory_open: bool = False,
        game_state_scripts: list[str] | None = None,
    ) -> dict[str, Any]:
        domain = self._layout_domain(state)
        status_payload = status_seed or self._status_seed(character_status)
        inventory_payload = inventory_window or build_inventory_window_vm(status_payload)
        return {
            "domain": domain,
            "payload_type": payload_type,
            "char_id": char_id,
            "transaction_id": transaction_id,
            "character_status": character_status,
            "scenario": scenario,
            "exploration": exploration,
            "exploration_local_map": exploration_local_map,
            "encounter": encounter,
            "arena": arena,
            "city_service": city_service,
            "combat": combat,
            "combat_screen": combat_screen,
            "combat_result": combat_result,
            "combat_result_screen": combat_result_screen,
            "combat_outcome_screen": combat_outcome_screen,
            "death": death,
            "loot": loot,
            "rift": rift,
            "combat_chat_session_id": getattr(combat_screen, "session_id", None),
            "background_url": background_url,
            "world_theme": world_theme,
            "nav": build_game_nav(state=domain, char_id=char_id),
            "status_seed": status_payload,
            "inventory_window": inventory_payload,
            "initial_inventory_open": initial_inventory_open,
            "debug_enabled": settings.debug,
            "game_state_scripts": game_state_scripts or [],
            "realtime_ws_url": settings.realtime_ws_url,
            "realtime_ws_endpoint": _realtime_ws_endpoint(settings.realtime_ws_url),
        }

    async def _inventory_window_state(
        self,
        token: str,
        *,
        char_id: int,
        character_status: CharacterActorCoreDTO | None,
        status_payload: dict[str, Any],
    ) -> tuple[bool, InventoryWindowDTO | Any]:
        initial_open = self._has_inventory_runtime_ref(character_status)
        if not initial_open:
            return False, build_inventory_window_vm(status_payload)

        response = await self.inventory_api.view(token, char_id=char_id)
        if response.payload is None:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Inventory payload is unavailable")

        from src.shared.schemas.inventory import InventoryWindowDTO

        return True, InventoryWindowDTO.model_validate(response.payload)

    @staticmethod
    def _has_inventory_runtime_ref(character_status: CharacterActorCoreDTO | None) -> bool:
        sessions = getattr(character_status, "sessions", None)
        if not isinstance(sessions, dict):
            return False
        return bool(sessions.get("inventory_id"))

    @staticmethod
    def _layout_domain(state: CoreDomain | str) -> str:
        domain = state.value if isinstance(state, CoreDomain) else str(state)
        if domain == CoreDomain.COMBAT_RESULT.value:
            return CoreDomain.COMBAT.value
        return domain

    @staticmethod
    def _status_seed(character_status: CharacterActorCoreDTO | None) -> dict[str, Any]:
        if character_status is None:
            return {
                "character_id": "",
                "hp": 0,
                "max_hp": 1,
                "energy": 0,
                "max_energy": 1,
                "stamina": 0,
                "max_stamina": 1,
                "avatar_url": None,
                "name": "NO_DATA",
                "symbiote": {},
                "symbiote_name": "NO_DATA",
            }
        vitals = character_status.vitals or {}
        bio = character_status.bio or {}
        symbiote = character_status.symbiote or {}
        symbiote_name = symbiote.get("name") or symbiote.get("symbiote_name") or settings.default_symbiote_name
        return {
            "character_id": character_status.char_id,
            "hp": _vital_current(vitals.get("hp")),
            "max_hp": _vital_max(vitals.get("hp")),
            "energy": _vital_current(vitals.get("energy")),
            "max_energy": _vital_max(vitals.get("energy")),
            "stamina": _vital_current(vitals.get("stamina")),
            "max_stamina": _vital_max(vitals.get("stamina")),
            "avatar_url": bio.get("avatar"),
            "name": bio.get("name"),
            "symbiote": symbiote,
            "symbiote_name": symbiote_name,
        }

    @staticmethod
    def _combat_status_seed(combat: CombatDashboardDTO) -> dict[str, Any]:
        hero = combat.hero
        return {
            "character_id": hero.actor_id,
            "hp": hero.vitals.hp_current,
            "max_hp": max(hero.vitals.hp_max, 1),
            "energy": hero.vitals.energy_current,
            "max_energy": max(hero.vitals.energy_max, 1),
            "stamina": hero.vitals.stamina_current,
            "max_stamina": max(hero.vitals.stamina_max, 1),
            "avatar_url": None,
            "name": hero.name,
            "symbiote": {},
            "symbiote_name": "NO_DATA",
        }

    @staticmethod
    def _empty_combat_status_seed(char_id: int) -> dict[str, Any]:
        return {
            "character_id": char_id,
            "hp": 0,
            "max_hp": 1,
            "energy": 0,
            "max_energy": 1,
            "stamina": 0,
            "max_stamina": 1,
            "avatar_url": None,
            "name": "NO_DATA",
            "symbiote": {},
            "symbiote_name": "NO_DATA",
        }


def _vital_current(value: Any) -> float:
    if isinstance(value, dict):
        return float(value.get("cur", 0))
    return 0.0


def _vital_max(value: Any) -> int:
    if isinstance(value, dict):
        return int(value.get("max", 1))
    return 1


def _return_context_from_transition(transition_context: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(transition_context, dict):
        return None
    raw = transition_context.get("return_context")
    return raw if isinstance(raw, dict) else None


def _city_service_screen_from_transition(
    transition_context: dict[str, Any] | None,
    transition_metadata: dict[str, Any] | None,
) -> str | None:
    return _transition_value("next_screen", transition_context, transition_metadata) or _transition_value(
        "screen",
        transition_context,
        transition_metadata,
    )


def _city_service_section_from_transition(
    transition_context: dict[str, Any] | None,
    transition_metadata: dict[str, Any] | None,
) -> str | None:
    section_id = _transition_value("section_id", transition_context, transition_metadata)
    if section_id:
        return section_id
    return_context = _return_context_from_transition(transition_context)
    if isinstance(return_context, dict):
        metadata = return_context.get("metadata")
        if isinstance(metadata, dict) and metadata.get("section_id"):
            return str(metadata["section_id"])
    return None


def _transition_value(
    key: str,
    transition_context: dict[str, Any] | None,
    transition_metadata: dict[str, Any] | None,
) -> str | None:
    for source in (transition_metadata, transition_context):
        if isinstance(source, dict) and source.get(key):
            return str(source[key])
    return_context = _return_context_from_transition(transition_context)
    if isinstance(return_context, dict):
        mapped_key = {
            "service_id": "source_service_id",
            "screen": "return_screen",
            "next_screen": "return_screen",
        }.get(key, key)
        if return_context.get(mapped_key):
            return str(return_context[mapped_key])
    return None


def _payload_value(payload: Any, key: str) -> Any:
    if isinstance(payload, dict):
        return payload.get(key)
    return getattr(payload, key, None)


def _post_combat_from_sources(
    transition_metadata: dict[str, Any] | None,
    sessions: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if isinstance(transition_metadata, dict) and isinstance(transition_metadata.get("post_combat"), dict):
        return transition_metadata["post_combat"]
    if isinstance(sessions, dict) and isinstance(sessions.get("post_combat"), dict):
        return sessions["post_combat"]
    return None
