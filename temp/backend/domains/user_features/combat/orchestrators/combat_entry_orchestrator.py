# apps/game_core/modules/combats/combat_entry_orchestrator.py
import uuid
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.domains.internal_systems.context_assembler.dtos import ContextRequestDTO, ContextResponseDTO
from src.backend.domains.internal_systems.context_assembler.service import ContextAssemblerService
from src.backend.domains.user_features.combat.orchestrators.handler.initialization.combat_lifecycle_service import (
    CombatLifecycleService,
)

if TYPE_CHECKING:
    from src.backend.domains.user_features.combat.orchestrators.handler.combat_session_service import (
        CombatSessionService,
    )


class CombatEntryOrchestrator:
    """
    Оркестратор входа в бой (v2.0).
    Диспетчер сценариев создания боевых сессий.
    Работает как Redis-bound сервис.
    """

    def __init__(
        self,
        lifecycle_service: CombatLifecycleService,
        session_service: "CombatSessionService",
        assembler: ContextAssemblerService,
    ):
        self.lifecycle = lifecycle_service
        self.session_service = session_service
        self.assembler = assembler

    async def get_entry_point(self, char_id: int, action: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Единая точка входа для создания боя.
        Выбирает сценарий на основе action.
        Возвращает результат операции (success).
        """
        log.info(f"CombatEntry | action='{action}' context={context}")

        try:
            if action == "standard_pve":
                return await self._handle_standard_pve(context)
            elif action == "shadow_duel":
                # char_id может прийти как аргумент или в контексте
                target_char_id = context.get("char_id") or char_id
                if not target_char_id:
                    raise ValueError("char_id is required for shadow_duel")
                return await self._handle_shadow_duel(int(target_char_id))
            elif action == "arena_match":
                return await self._handle_arena_match(context)
            elif action == "tutorial":
                # TODO: Реализовать туториал
                return {"success": False, "error": "Tutorial not implemented"}
            else:
                log.error(f"CombatEntry | Unknown action: {action}")
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:  # noqa: BLE001
            log.exception(f"CombatEntry | Failed to initialize combats: {e}")
            return {"success": False, "error": str(e)}

    # --- Сценарии (Pipelines) ---

    async def _handle_standard_pve(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Сценарий: Стандартный PvE бой.
        Вход: context["teams"] (список команд).
        """
        # 1. Prepare: Разбор команд и рандом цветов
        teams_data = context.get("teams", [])
        if not teams_data:
            raise ValueError("No teams provided for standard_pve")

        colors = ["blue", "red", "green", "yellow"]
        # TODO: Добавить shuffle(colors) если нужен рандом

        player_ids = []
        monster_ids = []
        team_map = []

        for i, team in enumerate(teams_data):
            color = colors[i] if i < len(colors) else f"team_{i}"
            t_players = team.get("players", [])
            t_monsters = team.get("monsters", [])

            player_ids.extend(t_players)
            monster_ids.extend(t_monsters)

            team_map.append({"color": color, "players": t_players, "monsters": t_monsters})

        # 2. Assemble: Получение UUID от Ассемблера через Direct Call
        # Дедупликация ID перед запросом
        unique_player_ids = list(set(player_ids))
        unique_monster_ids = list(set(monster_ids))

        data_refs = await self._assemble_data_refs(unique_player_ids, unique_monster_ids)

        # 3. Build: Сборка сессии
        session_teams_config: dict[str, dict[str, list]] = {}

        for team in team_map:
            color = team["color"]
            session_teams_config[color] = {"players": [], "monsters": []}

            for pid in team["players"]:
                if pid in data_refs.player:
                    session_teams_config[color]["players"].append({"id": pid, "ref": data_refs.player[pid]})

            for mid in team["monsters"]:
                if mid in data_refs.monster:
                    session_teams_config[color]["monsters"].append({"id": mid, "ref": data_refs.monster[mid]})

        return await self._finalize_session_creation("standard", session_teams_config, player_ids)

    async def _handle_shadow_duel(self, char_id: int) -> dict[str, Any]:
        """
        Сценарий: Бой с тенью.
        Вход: char_id.
        """
        # 1. Prepare & Assemble
        data_refs = await self._assemble_data_refs([char_id], [])

        if char_id not in data_refs.player:
            raise ValueError(f"Failed to assemble context for player {char_id}")

        player_ref = data_refs.player[char_id]

        # 2. Build
        # Lifecycle сам создаст Shadow-версию, передаем ref только раз
        session_teams_config: dict[str, dict[str, list]] = {
            "blue": {"players": [{"id": char_id, "ref": player_ref}], "monsters": []},
            "red": {
                "players": [{"id": f"-{char_id}", "ref": player_ref}],  # Явно указываем Shadow ID
                "monsters": [],
            },
        }

        return await self._finalize_session_creation("shadow", session_teams_config, [char_id])

    async def _handle_arena_match(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Сценарий: Арена.
        Вход: context["teams"] (словарь {color: [ids]}).
        """
        # 1. Prepare
        teams_dict = context.get("teams", {})

        player_ids = []
        monster_ids = []

        for _color, members in teams_dict.items():
            player_ids.extend(members.get("players", []))
            monster_ids.extend(members.get("monsters", []))

        # 2. Assemble
        # Дедупликация ID перед запросом
        unique_player_ids = list(set(player_ids))
        unique_monster_ids = list(set(monster_ids))

        data_refs = await self._assemble_data_refs(unique_player_ids, unique_monster_ids)

        # 3. Build
        session_teams_config: dict[str, dict[str, list]] = {}
        for color, members in teams_dict.items():
            session_teams_config[color] = {"players": [], "monsters": []}

            for pid in members.get("players", []):
                if pid in data_refs.player:
                    session_teams_config[color]["players"].append({"id": pid, "ref": data_refs.player[pid]})

            for mid in members.get("monsters", []):
                if mid in data_refs.monster:
                    session_teams_config[color]["monsters"].append({"id": mid, "ref": data_refs.monster[mid]})

        return await self._finalize_session_creation("arena", session_teams_config, player_ids)

    # --- Helpers ---

    async def _assemble_data_refs(self, player_ids: list[int], monster_ids: list[str]) -> ContextResponseDTO:
        """
        Вызывает ContextAssembler напрямую для подготовки данных в Redis.
        Возвращает маппинг ID -> RedisKey.
        """
        request = ContextRequestDTO(player_ids=player_ids, monster_ids=monster_ids, scope="combats")

        # Прямой вызов сервиса
        response = await self.assembler.assemble(request)

        if response.errors["player"] or response.errors["monster"]:
            log.warning(f"CombatEntry | Assembly errors: {response.errors}")

        return response

    async def _finalize_session_creation(
        self, mode: str, teams_config: dict, active_player_ids: list[int]
    ) -> dict[str, Any]:
        """
        Общий финал: Создание сессии в Lifecycle, линковка и возврат результата.
        """
        try:
            # Сначала проверяем данные (если бы была валидация), потом генерируем ID
            session_id = str(uuid.uuid4())

            # Вызываем Lifecycle для создания сессии
            await self.lifecycle.create_battle(session_id, {"mode": mode, "teams_config": teams_config})

            # Линковка игроков через SessionService (Facade)
            if active_player_ids:
                await self.session_service.link_players_to_session(active_player_ids, session_id)

            return {"success": True}

        except Exception as e:  # noqa: BLE001
            log.exception(f"CombatEntry | Finalize error: {e}")
            # TODO: Rollback (delete session)
            return {"success": False, "error": str(e)}
