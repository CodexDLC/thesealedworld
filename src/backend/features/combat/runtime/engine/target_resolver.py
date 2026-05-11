import random
from collections.abc import Callable  # noqa: TC003

from src.backend.features.combat.dto.ids import ActorId, ActorIdLike, normalize_actor_id
from src.backend.features.combat.dto.session import BattleMeta

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

    def resolve(self, source_id: ActorIdLike, target_raw: ActorIdLike | None, meta: BattleMeta) -> list[ActorId]:
        """
        Главный метод резолвинга.
        """
        if target_raw is None:
            return []

        source_actor_id = normalize_actor_id(source_id)

        # 1. Direct ID
        if isinstance(target_raw, int):
            return self._resolve_direct(target_raw, meta)

        if isinstance(target_raw, str) and target_raw.lstrip("-").isdigit():
            return self._resolve_direct(target_raw, meta)

        # 2. Alias Processing
        alias = str(target_raw).lower()

        # A. Static Strategies (from dict)
        handler = self._handlers.get(alias)
        if handler:
            return handler(source_actor_id, meta)

        # B. Dynamic Strategies (random_X)
        if alias.startswith("random_enemy_"):
            return self._resolve_random_enemies(source_actor_id, meta, alias)

        if self._is_known_actor_id(alias, meta):
            return self._resolve_direct(target_raw, meta)

        return []

    # --- Strategy Implementations ---

    def _resolve_self(self, source_id: ActorId, meta: BattleMeta) -> list[ActorId]:
        return [source_id]

    def _resolve_all_enemies(self, source_id: ActorId, meta: BattleMeta) -> list[ActorId]:
        my_team = self._get_team(source_id, meta)
        if not my_team:
            return []

        enemies: list[ActorId] = []
        dead_set = {normalize_actor_id(actor_id) for actor_id in meta.dead_actors}

        for team_name, members in meta.teams.items():
            if team_name != my_team:
                # Фильтруем мертвых
                alive_members = [
                    normalize_actor_id(member) for member in members if normalize_actor_id(member) not in dead_set
                ]
                enemies.extend(alive_members)
        return enemies

    def _resolve_all_allies(self, source_id: ActorId, meta: BattleMeta) -> list[ActorId]:
        my_team = self._get_team(source_id, meta)
        if not my_team:
            return []

        allies: list[ActorId] = []
        dead_set = {normalize_actor_id(actor_id) for actor_id in meta.dead_actors}

        for team_name, members in meta.teams.items():
            if team_name == my_team:
                alive_members = [
                    normalize_actor_id(member) for member in members if normalize_actor_id(member) not in dead_set
                ]
                allies.extend(alive_members)
        return allies

    def _resolve_random_enemies(self, source_id: ActorId, meta: BattleMeta, alias: str) -> list[ActorId]:
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

    def _get_team(self, char_id: ActorId, meta: BattleMeta) -> str | None:
        for team, members in meta.teams.items():
            if char_id in {normalize_actor_id(member) for member in members}:
                return team
        return None

    @staticmethod
    def _is_known_actor_id(actor_id: ActorId, meta: BattleMeta) -> bool:
        return any(actor_id == normalize_actor_id(member) for members in meta.teams.values() for member in members)

    @staticmethod
    def _resolve_direct(target_raw: ActorIdLike, meta: BattleMeta) -> list[ActorId]:
        target_id = normalize_actor_id(target_raw)
        dead_set = {normalize_actor_id(actor_id) for actor_id in meta.dead_actors}
        return [] if target_id in dead_set else [target_id]
