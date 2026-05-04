from typing import Any, Literal, cast

from loguru import logger as log

from src.backend.domains.user_features.combat.combat_engine.combat_data_service import CombatDataService
from src.backend.domains.user_features.combat.combat_engine.core.combat_victory_checker import VictoryChecker
from src.backend.domains.user_features.combat.combat_engine.logic.target_resolver import TargetResolver
from src.backend.domains.user_features.combat.dto import BattleMeta, CombatActionDTO, CombatMoveDTO
from src.backend.domains.user_features.combat.dto.combat_arq_dto import AiTurnRequestDTO, CollectorSignalDTO


class CombatCollector:
    """
    Коллектор (Collector Processor).
    Отвечает за сбор намерений (Moves), матчмейкинг и формирование задач для Исполнителя.
    Цикл: Load Snapshot -> Logic (AI, Instant, Exchange) -> Batch Save -> Return Tasks.
    """

    def __init__(self, data_service: CombatDataService):
        self.data_service = data_service
        self.target_resolver = TargetResolver()

    async def collect_actions(
        self, session_id: str, signal: CollectorSignalDTO | None = None
    ) -> tuple[int, list[AiTurnRequestDTO], str | None]:
        """
        Основной метод коллектора.
        Возвращает:
        - batch_size (int): Рекомендуемый размер батча для Исполнителя (0, если действий нет).
        - ai_tasks (List[AiTurnRequestDTO]): Список задач для AI агентов.
        - victory_result (str | None): Результат проверки победы ("team_name" / "draw" / None).
        """
        # 0. Backpressure Check (Защита от переполнения очереди)
        # Если очередь Исполнителя забита, не добавляем новые задачи.
        queue_size = await self.data_service.get_action_queue_size(session_id)
        if queue_size > 50:  # TODO: Вынести лимит в конфиг
            log.warning(f"Collector | Queue full ({queue_size}), skipping cycle. session_id={session_id}")
            return 0, [], None

        # 1. Load Snapshot (Meta + Moves + Targets)
        meta = await self.data_service.get_battle_meta(session_id)
        if not meta or not meta.active:
            return 0, [], None  # type: ignore # TODO: Fix later when refactoring Combat Engine

        # Получаем список всех участников из Meta
        all_actor_ids: list[int | str] = []
        for team_ids in meta.teams.values():
            all_actor_ids.extend(team_ids)

        # Грузим мувы всех участников
        moves_map = await self.data_service.get_intent_moves(session_id, all_actor_ids)

        # Грузим очереди целей (для AI)
        targets_map = await self.data_service.get_targets(session_id)

        # 2. Logic Processing
        actions_to_queue: list[CombatActionDTO] = []
        ai_tasks: list[AiTurnRequestDTO] = []

        # A. AI Check (с учетом целей)
        ai_tasks = self._check_ai_turns(session_id, meta, moves_map, targets_map)

        # B. Instant Harvesting (Items/Skills)
        instants, del_inst = self._harvest_instant(moves_map, meta)
        actions_to_queue.extend(instants)

        # C. Exchange Matchmaking (Combat + Force Attack)
        exchanges, del_exch = self._matchmake_exchange(moves_map, signal)
        actions_to_queue.extend(exchanges)

        # 3. Batch Save (Push Actions + Delete Moves)
        if actions_to_queue:
            # Атомарный перенос (Push + Delete)
            await self.data_service.transfer_actions(session_id, actions_to_queue)

        # 4. Calculate Batch Size (Dynamic)
        batch_size = 0
        if actions_to_queue:
            actors_count = len(all_actor_ids)
            # Формула: Чем больше актеров, тем меньше батч (чтобы не перегрузить воркер загрузкой контекста)
            # Base: 200. Min: 5. Max: 100.
            batch_size = min(100, max(5, int(200 / max(1, actors_count))))

        # 5. Victory Check (только если очередь actions пуста)
        # Если очередь пуста, значит все действия обработаны, можно проверить победу
        if queue_size == 0 and not actions_to_queue:
            victory_result = VictoryChecker.check_battle_end(meta)
            if victory_result:
                log.warning(
                    "VictoryDetected | session_id={session_id} winner={winner}",
                    session_id=session_id,
                    winner=victory_result,
                )
                # Возвращаем результат, чтобы CollectorTask запустил финализатор
                return 0, ai_tasks, victory_result

        return batch_size, ai_tasks, None

    def _check_ai_turns(
        self, session_id: str, meta: BattleMeta, moves_map: dict[str, Any], targets_map: dict[str, list[int]]
    ) -> list[AiTurnRequestDTO]:
        """
        Проверяет, кто из AI еще не сделал ход.
        Сравнивает очередь целей (targets) с заявленными мувами (exchange).
        Фильтрует мертвых акторов (оптимизация).
        """
        tasks = []
        dead_set = set(str(x) for x in meta.dead_actors)

        for actor_id_str, actor_type in meta.actors_info.items():
            if actor_type != "ai":
                continue

            if not actor_id_str.lstrip("-").isdigit():
                continue

            # Фильтруем мертвых ботов (оптимизация)
            if actor_id_str in dead_set:
                continue

            actor_id = int(actor_id_str)

            # 1. Получаем цели бота
            my_targets = targets_map.get(actor_id_str, [])
            if not my_targets:
                continue  # Нет целей - нет проблем (или бот спит)

            # 2. Получаем заявленные Exchange мувы
            actor_moves = moves_map.get(actor_id_str, {})
            exchange_moves = actor_moves.get("exchange", {})

            covered_targets = set()
            for move_json in exchange_moves.values():
                try:
                    # Парсим JSON, чтобы достать target_id
                    move = CombatMoveDTO(**move_json)
                    # payload теперь объект, используем getattr
                    tid = getattr(move.payload, "target_id", None)
                    if tid:
                        covered_targets.add(int(tid))
                except Exception:  # noqa: BLE001
                    pass

            # 3. Сравниваем и фильтруем мертвых из целей
            missing_targets_raw = list(set(my_targets) - covered_targets)
            # Фильтруем мертвых из списка целей
            missing_targets = [tid for tid in missing_targets_raw if str(tid) not in dead_set]

            if missing_targets:
                # Бот не покрыл все цели -> Ставим задачу с указанием целей
                tasks.append(AiTurnRequestDTO(session_id=session_id, bot_id=actor_id, missing_targets=missing_targets))

        return tasks

    def _harvest_instant(self, moves_map: dict[str, Any], meta: BattleMeta) -> tuple[list[CombatActionDTO], list[str]]:
        """Собирает Instant и Item мувы, резолвит цели."""
        actions = []
        to_delete = []

        for char_id, moves_data in moves_map.items():
            if not moves_data:
                continue

            # Объединяем обработку Item и Instant, так как логика таргетинга похожа
            for strategy in ["item", "instant"]:
                moves_dict = moves_data.get(strategy, {})

                for move_id, move_json in moves_dict.items():
                    try:
                        move = CombatMoveDTO(**move_json)

                        # Резолвинг целей через TargetResolver
                        # payload теперь объект, используем getattr
                        raw_target = getattr(move.payload, "target_id", None)
                        target_ids = self.target_resolver.resolve(int(char_id), raw_target, meta)  # type: ignore # TODO: Fix later when refactoring Combat Engine

                        # Записываем результат резолвинга в сам мув
                        move.targets = target_ids

                        # Создаем ОДИН Action на весь мув (с множеством целей)
                        # Используем cast для успокоения mypy
                        action_type = cast("Literal['exchange', 'item', 'instant', 'system']", strategy)
                        action = CombatActionDTO(action_type=action_type, move=move, is_forced=False)

                        actions.append(action)
                        to_delete.append(move_id)  # Удаляем мув после обработки

                    except Exception as e:  # noqa: BLE001
                        log.error(f"Collector | Failed to parse {strategy} move {move_id}: {e}")

        return actions, to_delete

    def _matchmake_exchange(
        self, moves_map: dict[str, Any], signal: CollectorSignalDTO | None = None
    ) -> tuple[list[CombatActionDTO], list[str]]:
        """Ищет пары для обмена ударами. Обрабатывает Force Attack по таймауту."""
        actions = []
        to_delete = []

        # Простой перебор (O(N^2) в худшем случае, но N мал)
        # Собираем пул всех exchange заявок
        pool = []
        for _char_id, moves_data in moves_map.items():
            exchanges = moves_data.get("exchange", {})
            for _move_id, move_json in exchanges.items():
                try:
                    move = CombatMoveDTO(**move_json)
                    # created_at removed from DTO, assume order is not critical or use move_id/timestamp if added back
                    # For now, just append
                    pool.append(move)
                except Exception:  # noqa: BLE001
                    pass

        # Сортируем по времени (FIFO) - removed as created_at is missing
        # pool.sort(key=lambda x: x.created_at)

        matched_ids = set()

        # 1. Normal Matchmaking
        for move_a in pool:
            if move_a.move_id in matched_ids:
                continue

            # payload теперь объект, используем getattr
            target_id = getattr(move_a.payload, "target_id", None)
            if not target_id:
                continue
            target_id = int(target_id)

            # Ищем ответный мув (B -> A)
            for move_b in pool:
                if move_b.move_id in matched_ids:
                    continue
                if int(move_b.char_id) != target_id:
                    continue

                # Проверяем, бьет ли B игрока A
                target_b = getattr(move_b.payload, "target_id", 0)
                if int(target_b) == int(move_a.char_id):
                    # ПАРА НАЙДЕНА!
                    action = CombatActionDTO(action_type="exchange", move=move_a, partner_move=move_b, is_forced=False)
                    actions.append(action)
                    matched_ids.add(move_a.move_id)
                    matched_ids.add(move_b.move_id)
                    to_delete.append(move_a.move_id)
                    to_delete.append(move_b.move_id)
                    break

        # 2. Force Attack Check (Timeout)
        if signal and signal.signal_type == "check_timeout" and signal.move_id:
            # Ищем мув, который вызвал таймаут
            # Если он еще в пуле (не сматчился выше) -> Force Attack

            # Если move_id="batch", мы не знаем конкретный ID.
            # Но для AI мы ставим "batch".
            # Значит, если "batch", мы должны проверить ВСЕ мувы AI?
            # Или просто пройтись по всем оставшимся в пуле и проверить их возраст?
            # Давайте пока поддержим конкретный ID и "batch" (как Force All Old).

            force_candidates = []

            if signal.move_id == "batch":
                # Force all unmatched moves for this char_id (if provided)
                # Signal содержит char_id.
                for move in pool:
                    if move.move_id not in matched_ids and int(move.char_id) == signal.char_id:
                        force_candidates.append(move)
            else:
                # Specific move
                for move in pool:
                    if move.move_id == signal.move_id and move.move_id not in matched_ids:
                        force_candidates.append(move)
                        break

            for move in force_candidates:
                # Создаем Force Action (односторонний)
                action = CombatActionDTO(
                    action_type="exchange",  # Или "forced"? Оставим exchange, но is_forced=True
                    move=move,
                    partner_move=None,  # Нет партнера
                    is_forced=True,
                )
                actions.append(action)
                matched_ids.add(move.move_id)
                to_delete.append(move.move_id)
                log.warning(f"Collector | Force Attack triggered for {move.move_id}")

        return actions, to_delete
