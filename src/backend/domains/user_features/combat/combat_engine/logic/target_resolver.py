import random
from collections.abc import Callable

from src.backend.domains.user_features.combat.dto.combat_session_dto import BattleMeta

# Конфигурация стратегий (Alias -> Method Name)
TARGET_STRATEGIES = {
    "self": "_resolve_self",
    "all_enemies": "_resolve_all_enemies",
    "all_allies": "_resolve_all_allies",
    # Динамические (random_X) обрабатываются отдельно в resolve
}


class TargetResolver:
    """
    Logic Service.
    Превращает абстрактные цели (строки-алиасы) в конкретные списки ID участников.
    """

    def __init__(self):
        # Инициализация маппинга: Alias -> Callable Method
        self._handlers: dict[str, Callable] = {}
        for alias, method_name in TARGET_STRATEGIES.items():
            if hasattr(self, method_name):
                self._handlers[alias] = getattr(self, method_name)

    def resolve(self, source_id: int, target_raw: int | str | None, meta: BattleMeta) -> list[int]:
        """
        Главный метод резолвинга.
        """
        if target_raw is None:
            return []

        # 1. Direct ID (int or numeric string)
        if isinstance(target_raw, int):
            return [target_raw]

        if isinstance(target_raw, str) and target_raw.lstrip("-").isdigit():
            return [int(target_raw)]

        # 2. Alias Processing
        alias = str(target_raw).lower()

        # A. Static Strategies (from dict)
        handler = self._handlers.get(alias)
        if handler:
            return handler(source_id, meta)

        # B. Dynamic Strategies (random_X)
        if alias.startswith("random_enemy_"):
            return self._resolve_random_enemies(source_id, meta, alias)

        return []

    # --- Strategy Implementations ---

    def _resolve_self(self, source_id: int, meta: BattleMeta) -> list[int]:
        return [source_id]

    def _resolve_all_enemies(self, source_id: int, meta: BattleMeta) -> list[int]:
        my_team = self._get_team(source_id, meta)
        if not my_team:
            return []

        enemies = []
        dead_set = set(meta.dead_actors)

        for team_name, members in meta.teams.items():
            if team_name != my_team:
                # Фильтруем мертвых
                alive_members = [int(m) for m in members if m not in dead_set]
                enemies.extend(alive_members)
        return enemies

    def _resolve_all_allies(self, source_id: int, meta: BattleMeta) -> list[int]:
        my_team = self._get_team(source_id, meta)
        if not my_team:
            return []

        allies = []
        dead_set = set(meta.dead_actors)

        for team_name, members in meta.teams.items():
            if team_name == my_team:
                alive_members = [int(m) for m in members if m not in dead_set]
                allies.extend(alive_members)
        return allies

    def _resolve_random_enemies(self, source_id: int, meta: BattleMeta, alias: str) -> list[int]:
        try:
            # Format: random_enemy_3
            count = int(alias.split("_")[-1])
            enemies = self._resolve_all_enemies(source_id, meta)  # Уже отфильтрованы
            if not enemies:
                return []

            return random.sample(enemies, min(len(enemies), count))
        except (ValueError, IndexError):
            return []

    # --- Helpers ---

    def _get_team(self, char_id: int, meta: BattleMeta) -> str | None:
        for team, members in meta.teams.items():
            if char_id in members:
                return team
        return None
