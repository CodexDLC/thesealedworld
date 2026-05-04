# apps/game_core/modules/combats/session/runtime/combat_view_service.py
"""
Файл: app/game_core/modules/combats/session/combat_view_service.py
"""

import contextlib
from collections import defaultdict

from src.backend.domains.user_features.combat.combat_engine.mechanics.feint_service import FeintService
from src.backend.domains.user_features.combat.dto.combat_actor_dto import ActorSnapshot
from src.backend.domains.user_features.combat.dto.combat_session_dto import BattleContext
from src.shared.schemas.combat import (
    ActorFullInfo,
    ActorShortInfo,
    CombatDashboardDTO,
    CombatLogDTO,
    CombatLogEntryDTO,
)


class CombatViewService:
    """
    Read Model (Pure Mapper) v3.0.
    Преобразует BattleContext (из ActorManager) в DTO для клиента.
    Не имеет зависимостей от Redis/Manager.
    """

    def build_dashboard_dto_from_context(self, char_id: int, context: BattleContext) -> CombatDashboardDTO:
        """
        Собирает CombatDashboardDTO из BattleContext.
        """
        # 1. Находим себя
        # context.actors ключи - строки
        me = context.actors.get(str(char_id))
        if not me:
            raise ValueError(f"Player {char_id} not found in context")

        my_team = me.team

        # 2. Определяем статус и цель
        status = "active"
        target_info: ActorFullInfo | None = None

        # Глобальный статус
        if context.meta.active == 0 or context.meta.winner:
            status = "finished"
        elif me.state.is_dead:
            # Если мертв - статус active (зритель), но цели нет
            status = "active"
        else:
            # Проверка: Есть ли цель в очереди?
            # targets: {char_id: [target_id, ...]}
            my_targets = context.targets.get(str(char_id), [])

            if not my_targets:
                status = "waiting"
            else:
                # Цель есть -> Active
                target_id = my_targets[0]
                target_actor = context.actors.get(str(target_id))

                if target_actor:
                    target_info = self._map_actor_full(target_actor)
                else:
                    # Цель в очереди есть, но данные не загружены (странно, но бывает)
                    # Считаем waiting
                    status = "waiting"

        # 3. Парсим списки (Allies / Enemies)
        allies: list[ActorShortInfo] = []
        enemies: list[ActorShortInfo] = []

        # Текущий ID цели (для подсветки в списке)
        current_target_id = target_info.char_id if target_info else None

        for aid, actor in context.actors.items():
            if str(aid) == str(char_id):
                continue  # Себя в списки не добавляем

            is_target = int(aid) == current_target_id
            short_dto = self._map_actor_short(actor, is_target)

            if actor.team == my_team:
                allies.append(short_dto)
            else:
                enemies.append(short_dto)

        # Сортировка: Живые выше, Мертвые ниже
        allies.sort(key=lambda x: (x.is_dead, -x.hp_percent))
        enemies.sort(key=lambda x: (x.is_dead, -x.hp_percent))

        # 4. Собираем DTO
        return CombatDashboardDTO(
            turn_number=context.meta.step_counter,
            status=status,
            hero=self._map_actor_full(me),
            target=target_info,
            allies=allies,
            enemies=enemies,
            winner_team=context.meta.winner,
        )

    @staticmethod
    def build_logs_dto(raw_logs: list[str], page: int = 0) -> CombatLogDTO:
        """
        Собирает CombatLogDTO из списка сырых логов.
        """
        page_size = 20
        total = len(raw_logs)

        start = (page - 1) * page_size
        end = start + page_size

        chunk_raw = raw_logs[start:end]
        chunk_parsed = []

        for log_json in chunk_raw:
            with contextlib.suppress(Exception):
                entry = CombatLogEntryDTO.model_validate_json(log_json)
                chunk_parsed.append(entry)

        return CombatLogDTO(logs=chunk_parsed, page=page, total=total)

    # --- MAPPERS ---

    @staticmethod
    def _map_actor_full(actor: ActorSnapshot) -> ActorFullInfo:
        """Полная инфа (Hero / Target)."""
        # Получаем тип оружия из layout (main_hand)
        # layout теперь dict[str, str], где ключ - слот, значение - skill_key
        layout_skill = actor.loadout.layout.get("main_hand", "unarmed")

        # Получаем финты для UI
        feints_hand = FeintService.get_hand_for_dashboard(actor.meta)

        # Подсчет полных токенов (свободные + в руке)
        total_tokens: dict[str, int] = defaultdict(int)

        # 1. Свободные
        for k, v in actor.state.tokens.items():
            total_tokens[k] += v

        # 2. В руке (замороженные)
        # hand: {feint_id: {hit: 2, crit: 1}}
        for cost in actor.meta.feints.hand.values():
            for token_type, amount in cost.items():
                total_tokens[token_type] += amount

        return ActorFullInfo(
            char_id=actor.char_id,
            name=actor.meta.name,  # Имя в meta
            team=actor.team,
            is_dead=actor.state.is_dead,  #
            hp_current=actor.state.hp,
            hp_max=actor.state.max_hp,
            energy_current=actor.state.en,
            energy_max=actor.state.max_en,
            weapon_type=layout_skill,
            tokens=dict(total_tokens),  # Отправляем сумму
            effects=[e.effect_id for e in actor.active_effects],  # Используем active_effects
            feints=feints_hand,  # NEW: Feints
        )

    @staticmethod
    def _map_actor_short(actor: ActorSnapshot, is_target: bool) -> ActorShortInfo:
        """Краткая инфа (Lists)."""
        hp_pct = 0
        if actor.state.max_hp > 0:
            hp_pct = int((actor.state.hp / actor.state.max_hp) * 100)

        return ActorShortInfo(
            char_id=actor.char_id,
            name=actor.meta.name,  # Имя в meta
            hp_percent=hp_pct,
            is_dead=actor.state.is_dead,
            is_target=is_target,
        )
