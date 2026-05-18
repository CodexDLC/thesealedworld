# src/backend/features/exploration/services/exploration_service.py
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from pydantic import ValidationError

from src.backend.features.exploration.dto.config import ExplorationConfig
from src.backend.features.exploration.resources.service_registry import get_service_entry
from src.backend.features.exploration.runtime.city_map import build_city_map_payload
from src.backend.features.exploration.runtime.encounter.bypass import (
    bypass_chance_percent,
    calculate_bypass_chance,
    encounter_with_bypass_chance,
)
from src.backend.features.exploration.runtime.navigation import NavigationEngine
from src.shared.enums import CoreDomain
from src.shared.schemas.exploration import (
    AlertHudDTO,
    EncounterDTO,
    ExplorationHudDTO,
    ExplorationListDTO,
    ListItemDTO,
    WorldNavigationDTO,
)
from src.shared.schemas.response import ServiceResult
from src.shared.schemas.world_theme import WorldThemeDTO

if TYPE_CHECKING:
    from src.backend.features.exploration.integrations.encounter_integration import EncounterIntegration
    from src.backend.features.exploration.integrations.system_integrator import ExplorationSystemIntegrator
    from src.backend.features.exploration.runtime.encounter import EncounterEngine

log = logging.getLogger(__name__)


class ExplorationService:
    """
    Основной сервис домена Exploration.
    Координирует перемещение, генерацию событий и сборку UI.
    """

    def __init__(
        self,
        integrator: ExplorationSystemIntegrator,
        encounter_engine: EncounterEngine,
        encounter_integration: EncounterIntegration | None = None,
    ):
        self._integrator = integrator
        self._encounter_engine = encounter_engine
        self._encounter_integration = encounter_integration

    # =========================================================================
    # CORE ACTIONS
    # =========================================================================

    async def move(
        self, char_id: int, direction: str | None = None, target_id: str | None = None
    ) -> WorldNavigationDTO | EncounterDTO:
        """
        Попытка перемещения.
        Принимает либо direction (legacy n, s, w, e), либо target_id (52_51).
        """
        current_loc_id = await self._integrator.get_player_location_id(char_id)
        if not current_loc_id:
            current_loc_id = ExplorationConfig.DEFAULT_SPAWN_POINT

        active_encounter = await self._get_active_encounter(char_id)
        if active_encounter is not None:
            return active_encounter.payload

        loc_data = await self._integrator.get_location_data(current_loc_id)

        if not loc_data:
            log.error("ExplorationService | loc_not_found char_id=%s loc=%s", char_id, current_loc_id)
            return await self._build_navigation_dto(char_id, current_loc_id, {})

        exits = loc_data.get("exits", {})
        target_loc_id = None

        # 1. Resolve Target ID
        if target_id and (f"nav:{target_id}" in exits or target_id in exits):
            target_loc_id = target_id
        elif direction and (f"nav:{direction}" in exits or direction in exits):
            target_loc_id = direction

        if not target_loc_id:
            log.warning("ExplorationService | invalid_move char_id=%s target=%s dir=%s", char_id, target_id, direction)
            return await self._build_navigation_dto(char_id, current_loc_id, loc_data)

        # 2. Encounter Check (before moving)
        target_loc_data = await self._integrator.get_location_data(target_loc_id)
        if target_loc_data:
            skills = await self._integrator.get_actor_skills(char_id)
            scouting = self._encounter_skill_value(skills, trigger="move")

            encounter = await self._encounter_engine.try_generate_encounter(
                char_id=char_id,
                location_data=target_loc_data,
                scouting_skill=scouting,
                trigger="move",
                loc_id=target_loc_id,
            )

            if encounter:
                # Still move the player to the target location where encounter happens
                await self._integrator.move_player(char_id, current_loc_id, target_loc_id)
                encounter = await self._attach_navigation_snapshot(char_id, target_loc_id, target_loc_data, encounter)
                encounter = await self._attach_bypass_chance(char_id, encounter)
                await self._persist_encounter(char_id, encounter)
                return encounter

        # 3. Finalize Move
        await self._integrator.move_player(char_id, current_loc_id, target_loc_id)
        return await self.look_around(char_id)

    async def look_around(self, char_id: int) -> WorldNavigationDTO | EncounterDTO:
        """
        Обновление данных текущей локации (без движения).
        """
        loc_id = await self._integrator.get_player_location_id(char_id)
        if not loc_id:
            loc_id = ExplorationConfig.DEFAULT_SPAWN_POINT

        active_encounter = await self._get_active_encounter(char_id)
        if active_encounter is not None:
            return active_encounter.payload

        loc_data = await self._integrator.get_location_data(loc_id) or {}

        return await self._build_navigation_dto(char_id, loc_id, loc_data)

    async def interact(
        self, char_id: int, action: str, target_id: str | None = None
    ) -> WorldNavigationDTO | EncounterDTO | ExplorationListDTO | ServiceResult:
        """
        Обработка контекстных действий (Search, Battles, Bypass, etc).
        """
        loc_id = await self._integrator.get_player_location_id(char_id)
        if not loc_id:
            loc_id = ExplorationConfig.DEFAULT_SPAWN_POINT

        loc_data = await self._integrator.get_location_data(loc_id) or {}
        active_encounter = await self._get_active_encounter(char_id)

        # --- Encounter Reactions ---
        if action == "attack":
            # For now, we assume Combat session was already created by EncounterEngine
            # This action just transitions the client state.
            return ServiceResult(data={"status": "entering_combat"}, next_state=CoreDomain.COMBAT)

        if action == "bypass":
            if active_encounter is not None:
                skills = await self._integrator.get_actor_skills(char_id)
                chance = calculate_bypass_chance(skills)
                roll = random.random()
                if roll <= chance:
                    await self._clear_active_encounter(char_id, active_encounter.encounter_id)
                    dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
                    dto.hud = AlertHudDTO(message="Опасность миновала. Вы решили обойти угрозу.", style="info")
                    return dto

                encounter = encounter_with_bypass_chance(
                    active_encounter.payload,
                    chance,
                    result={
                        "success": False,
                        "chance_percent": bypass_chance_percent(chance),
                        "roll_percent": bypass_chance_percent(roll),
                    },
                )
                await self._patch_active_encounter_payload(active_encounter.encounter_id, encounter)
                return ServiceResult(
                    data={
                        "status": "bypass_failed_entering_combat",
                        "encounter_id": active_encounter.encounter_id,
                        "bypass_result": encounter.metadata.get("bypass_result"),
                    },
                    next_state=CoreDomain.COMBAT,
                )
            return await self.look_around(char_id)

        if active_encounter is not None:
            return active_encounter.payload

        # --- Exploration Actions ---
        if action == "search":
            skills = await self._integrator.get_actor_skills(char_id)
            scouting = self._encounter_skill_value(skills, trigger="search")

            search_encounter = await self._encounter_engine.try_generate_encounter(
                char_id=char_id, location_data=loc_data, scouting_skill=scouting, trigger="search", loc_id=loc_id
            )
            if search_encounter:
                search_encounter = await self._attach_navigation_snapshot(char_id, loc_id, loc_data, search_encounter)
                search_encounter = await self._attach_bypass_chance(char_id, search_encounter)
                await self._persist_encounter(char_id, search_encounter)
                return search_encounter

            # Empty search -> Alert HUD
            dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
            dto.hud = AlertHudDTO(message="Вы ничего не нашли.", style="info")
            return dto

        if action == "battles":
            return await self._scan_battles(char_id, loc_id, loc_data)

        # Default fallback
        return await self.look_around(char_id)

    async def use_service(self, char_id: int, service_id: str) -> WorldNavigationDTO | EncounterDTO | ServiceResult:
        loc_id = await self._integrator.get_player_location_id(char_id)
        if not loc_id:
            loc_id = ExplorationConfig.DEFAULT_SPAWN_POINT

        active_encounter = await self._get_active_encounter(char_id)
        if active_encounter is not None:
            return active_encounter.payload

        loc_data = await self._integrator.get_location_data(loc_id) or {}
        if not self._service_allowed_in_location(loc_data, service_id):
            log.warning("ExplorationService | service_denied char_id=%s loc=%s service=%s", char_id, loc_id, service_id)
            dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
            dto.hud = AlertHudDTO(message="Сервис недоступен из этой локации.", style="danger")
            return dto

        entry = get_service_entry(service_id)
        if entry is None:
            log.warning(
                "ExplorationService | service_unknown char_id=%s loc=%s service=%s", char_id, loc_id, service_id
            )
            dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
            dto.hud = AlertHudDTO(message="Сервис пока не подключен.", style="info")
            return dto

        if entry.access_policy != "public":
            log.warning(
                "ExplorationService | service_access_not_implemented char_id=%s loc=%s service=%s policy=%s",
                char_id,
                loc_id,
                service_id,
                entry.access_policy,
            )
            dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
            dto.hud = AlertHudDTO(message="Доступ к сервису пока не подключен.", style="info")
            return dto

        return ServiceResult(
            data={
                "service_id": service_id,
                "location_id": loc_id,
                "label": entry.label,
                **entry.metadata,
            },
            next_state=entry.target_state,
        )

    # =========================================================================
    # LOGIC: Battle Scanner
    # =========================================================================

    async def _scan_battles(self, char_id: int, loc_id: str, loc_data: dict) -> WorldNavigationDTO | ExplorationListDTO:
        """
        Сканирует бои в локации.
        """
        battles = await self._integrator.get_battles(loc_id)

        if not battles:
            dto = await self._build_navigation_dto(char_id, loc_id, loc_data)
            dto.hud = AlertHudDTO(message="В локации тихо. Боев не обнаружено.", style="info")
            return dto

        items = []
        for bid, desc in battles.items():
            items.append(ListItemDTO(id=bid, text=desc, action=f"spectate:{bid}"))

        return ExplorationListDTO(
            title="⚔️ Активные бои",
            items=items,
            page=1,
            total_pages=1,
            back_action="look_around",
        )

    @staticmethod
    def _service_allowed_in_location(loc_data: dict, service_id: str) -> bool:
        services = loc_data.get("services")
        if isinstance(services, list) and service_id in {str(item) for item in services}:
            return True

        exits = loc_data.get("exits", {})
        if not isinstance(exits, dict):
            return False
        return f"svc:{service_id}" in exits or service_id in exits

    # =========================================================================
    # HELPERS: DTO Builder
    # =========================================================================

    async def _build_navigation_dto(self, char_id: int, loc_id: str, loc_data: dict) -> WorldNavigationDTO:
        """
        Сборка DTO для клиента (Карта).
        """
        players_count = await self._integrator.get_players_count(loc_id, exclude_char_id=char_id)
        battles = await self._integrator.get_battles(loc_id)
        battles_count = len(battles)

        flags = loc_data.get("flags", {})
        anchor_influence = loc_data.get("anchor_influence", {})
        if not isinstance(anchor_influence, dict):
            anchor_influence = {}
        world_theme = WorldThemeDTO.model_validate(loc_data.get("world_theme") or {})
        if world_theme.loc_id is None:
            world_theme.loc_id = loc_id

        # Используем NavigationEngine для сборки сетки
        exits = loc_data.get("exits", {})
        world_zone = loc_data.get("world_zone", {})
        world_zone = world_zone if isinstance(world_zone, dict) else {}
        grid = NavigationEngine.build_grid(loc_id, exits, flags, anchor_influence)
        navigation = NavigationEngine.build_actions(loc_id, exits, flags, anchor_influence)

        is_safe_zone = NavigationEngine.is_safe_context(flags, anchor_influence)
        threat = self._safe_threat(anchor_influence.get("threat", flags.get("threat", 0.0)))

        hud = ExplorationHudDTO(
            threat=threat,
            threat_tier=int(flags.get("threat_tier", 0)),
            players_count=players_count,
            battles_count=battles_count,
            is_safe_zone=is_safe_zone,
            dominant_anchor=anchor_influence.get("dominant_anchor"),
            ambient_tags=anchor_influence.get("tags", []),
        )

        dto = WorldNavigationDTO(
            loc_id=loc_id,
            title=loc_data.get("name", "Unknown"),
            description=loc_data.get("description", "..."),
            background_url=loc_data.get("background_url"),
            anchor_influence=anchor_influence,
            world_theme=world_theme,
            visual_objects=[],
            players_nearby=players_count,
            grid=grid,
            navigation=navigation,
            hud=hud,
            threat_tier=int(flags.get("threat_tier", 0)),
            is_safe_zone=is_safe_zone,
            zone_id=str(loc_data.get("zone_id") or world_zone.get("id") or ""),
            terrain=str(loc_data.get("terrain") or ""),
            biome_id=str(loc_data.get("biome_id") or world_zone.get("biome_id") or ""),
            node_type=str(loc_data.get("node_type") or ""),
            zone_archetype=str(world_zone.get("zone_archetype") or ""),
            navigation_profile_id=str(
                loc_data.get("navigation_profile_id") or world_zone.get("navigation_profile_id") or ""
            ),
            buildable_kind=loc_data.get("buildable_kind"),
            landmark_profile=loc_data.get("landmark_profile") or world_zone.get("landmark_profile"),
            movement_profile=_safe_dict(loc_data.get("movement_profile")),
            world_zone=world_zone,
            city_map=build_city_map_payload(loc_id, loc_data),
        )
        if dto.world_theme is not None and hasattr(dto.world_theme, "model_dump"):
            await self._integrator.set_world_theme(char_id, dto.world_theme.model_dump(mode="json"))
        return dto

    @staticmethod
    def _safe_threat(value: object) -> float:
        try:
            return max(0.0, min(1.0, float(cast("Any", value))))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _encounter_skill_value(skills: dict[str, Any], *, trigger: str) -> float:
        skill_key = "skill_pathfinder" if trigger == "move" else "skill_scouting"
        raw = skills.get(skill_key, 0.0)
        try:
            return max(0.0, float(cast("Any", raw)))
        except (TypeError, ValueError):
            return 0.0

    async def _get_active_encounter(self, char_id: int) -> _ActiveEncounter | None:
        if self._encounter_integration is None:
            return None

        encounter_id = await self._encounter_integration.get_active_encounter_id(char_id)
        if encounter_id is None:
            return None

        session = await self._encounter_integration.get_encounter_session(encounter_id)
        if session is None:
            log.warning("ExplorationService | stale_encounter_ref char_id=%s encounter=%s", char_id, encounter_id)
            await self._encounter_integration.detach_encounter_session(char_id)
            return None

        payload = session.get("payload", session)
        if not isinstance(payload, dict):
            await self._clear_active_encounter(char_id, encounter_id)
            return None
        try:
            encounter = EncounterDTO.model_validate(payload)
        except ValidationError:
            log.warning("ExplorationService | invalid_encounter_session char_id=%s encounter=%s", char_id, encounter_id)
            await self._clear_active_encounter(char_id, encounter_id)
            return None
        if not isinstance(encounter.metadata.get("navigation"), dict):
            loc_id = await self._integrator.get_player_location_id(char_id)
            if loc_id:
                loc_data = await self._integrator.get_location_data(loc_id) or {}
                encounter = await self._attach_navigation_snapshot(char_id, loc_id, loc_data, encounter)
                try:
                    await self._encounter_integration.patch_encounter_session(
                        encounter_id,
                        {"payload": encounter.model_dump(mode="json")},
                    )
                except Exception:  # noqa: BLE001
                    log.warning(
                        "ExplorationService | encounter_navigation_snapshot_patch_failed char_id=%s encounter=%s",
                        char_id,
                        encounter_id,
                    )
        encounter = await self._attach_bypass_chance(char_id, encounter)
        return _ActiveEncounter(encounter_id=encounter_id, payload=encounter)

    async def _persist_encounter(self, char_id: int, encounter: EncounterDTO) -> None:
        if self._encounter_integration is None:
            return
        payload = encounter.model_dump(mode="json")
        await self._encounter_integration.create_encounter_session(
            encounter.id,
            {
                "encounter_id": encounter.id,
                "char_id": char_id,
                "status": "pending",
                "payload": payload,
            },
        )
        await self._encounter_integration.attach_encounter_session(char_id, encounter.id)

    async def _attach_navigation_snapshot(
        self,
        char_id: int,
        loc_id: str,
        loc_data: dict,
        encounter: EncounterDTO,
    ) -> EncounterDTO:
        navigation = await self._build_navigation_dto(char_id, loc_id, loc_data)
        metadata = dict(encounter.metadata or {})
        metadata["navigation"] = navigation.model_dump(mode="json")
        return encounter.model_copy(update={"metadata": metadata})

    async def _attach_bypass_chance(self, char_id: int, encounter: EncounterDTO) -> EncounterDTO:
        skills = await self._integrator.get_actor_skills(char_id)
        return encounter_with_bypass_chance(encounter, calculate_bypass_chance(skills))

    async def _patch_active_encounter_payload(self, encounter_id: str, encounter: EncounterDTO) -> None:
        if self._encounter_integration is None:
            return
        try:
            await self._encounter_integration.patch_encounter_session(
                encounter_id,
                {"payload": encounter.model_dump(mode="json")},
            )
        except Exception:  # noqa: BLE001
            log.warning(
                "ExplorationService | encounter_bypass_patch_failed encounter=%s",
                encounter_id,
            )

    async def _clear_active_encounter(self, char_id: int, encounter_id: str) -> None:
        if self._encounter_integration is None:
            return
        await self._encounter_integration.clear_encounter_session(encounter_id)
        await self._encounter_integration.detach_encounter_session(char_id)


def _safe_dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass(frozen=True, slots=True)
class _ActiveEncounter:
    encounter_id: str
    payload: EncounterDTO
