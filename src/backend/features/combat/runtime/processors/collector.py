from typing import Any, Literal, cast

from loguru import logger as log

from src.backend.features.combat.dto import BattleMeta, CombatActionDTO, CombatMoveDTO
from src.backend.features.combat.dto.ids import ActorId, ActorIdLike, normalize_actor_id
from src.backend.features.combat.dto.worker import AiTurnRequestDTO, CollectorSignalDTO
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.engine.target_resolver import TargetResolver
from src.backend.features.combat.runtime.engine.victory_checker import VictoryChecker
from src.backend.features.combat.runtime.services.data_service import CombatDataService

COMBAT_ACTION_QUEUE_LIMIT = 50


class CombatCollector:
    """Collect runtime intents and convert them into executable combat actions.

    The collector is the matchmaker stage between the intent buffer and the
    executor queue. It reads pending moves and target queues, identifies missing
    AI actions, resolves instant/item targeting, matches exchange pairs, creates
    forced exchanges on timeout, and atomically transfers runnable actions into
    the executor action queue.
    """

    def __init__(self, data_service: CombatDataService):
        self.data_service = data_service
        self.target_resolver = TargetResolver()

    async def collect_actions(
        self, session_id: str, signal: CollectorSignalDTO | None = None
    ) -> tuple[int, list[AiTurnRequestDTO], str | None]:
        """Collect runnable combat actions for one combat session.

        Args:
            session_id: Active combat session id.
            signal: Optional collector signal describing heartbeat/timeout cause.

        Returns:
            A tuple of ``(batch_size, ai_tasks, victory_result)`` where
            ``batch_size`` is the recommended executor pull size,
            ``ai_tasks`` contains uncovered NPC target requests, and
            ``victory_result`` contains the winning team when battle end is
            detectable without new runnable actions.
        """
        # 0. Load Meta first so stale delayed timeout jobs from finished
        # sessions exit before touching queues, moves, or targets.
        meta = await self.data_service.get_battle_meta(session_id)
        if not meta or not meta.active:
            return 0, [], None  # type: ignore # TODO: Fix later when refactoring Combat Engine

        # 1. Backpressure Check (Защита от переполнения очереди)
        # Если очередь Исполнителя забита, не добавляем новые задачи.
        queue_size = await self.data_service.get_action_queue_size(session_id)
        if queue_size > COMBAT_ACTION_QUEUE_LIMIT:
            log.bind(queue_size=queue_size, session_id=session_id).warning("CollectorQueueFull")
            return 0, [], None

        # Получаем список всех участников из Meta
        all_actor_ids: list[ActorIdLike] = []
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
        if instants:
            log.bind(
                session_id=session_id,
                instants_count=len(instants),
                signal_type=signal.signal_type if signal else None,
            ).info("CollectorHarvestedInstants")

        # C. Exchange Matchmaking (Combat + Force Attack)
        exchanges, del_exch = self._matchmake_exchange(moves_map, signal)
        actions_to_queue.extend(exchanges)

        # 3. Batch Save (Push Actions + Delete Moves)
        if actions_to_queue:
            # Атомарный перенос (Push + Delete)
            await self.data_service.transfer_actions(session_id, actions_to_queue)
            queue_size = await self.data_service.get_action_queue_size(session_id)

        # 4. Calculate Batch Size (Dynamic)
        batch_size = 0
        if queue_size > 0:
            actors_count = len(all_actor_ids)
            # Формула: Чем больше актеров, тем меньше батч (чтобы не перегрузить воркер загрузкой контекста)
            # Base: 200. Min: 5. Max: 100.
            batch_size = min(100, max(5, int(200 / max(1, actors_count))))

        # 5. Victory Check (только если очередь actions пуста)
        # Если очередь пуста, значит все действия обработаны, можно проверить победу
        if queue_size == 0 and not actions_to_queue:
            victory_result = VictoryChecker.check_battle_end(meta)
            if victory_result:
                log.bind(session_id=session_id, winner=victory_result).warning("VictoryDetected")
                # Возвращаем результат, чтобы CollectorTask запустил финализатор
                return 0, ai_tasks, victory_result

        return batch_size, ai_tasks, None

    def _check_ai_turns(
        self, session_id: str, meta: BattleMeta, moves_map: dict[str, Any], targets_map: dict[str, list[ActorId]]
    ) -> list[AiTurnRequestDTO]:
        """Return AI task requests for bots that still have uncovered targets."""
        tasks: list[AiTurnRequestDTO] = []
        dead_set = set(str(x) for x in meta.dead_actors)

        for actor_id_str, actor_type in meta.actors_info.items():
            if actor_type != "ai":
                continue

            # Фильтруем мертвых ботов (оптимизация)
            if actor_id_str in dead_set:
                continue

            actor_id = normalize_actor_id(actor_id_str)

            # 1. Получаем цели бота
            my_targets = targets_map.get(actor_id_str, [])
            if not my_targets:
                continue  # Нет целей - нет проблем (или бот спит)

            # 2. Получаем заявленные Exchange мувы
            actor_moves = moves_map.get(actor_id_str, {})
            exchange_moves = actor_moves.get("exchange", {})

            covered_targets: set[ActorId] = set()
            for move_json in exchange_moves.values():
                try:
                    # Парсим JSON, чтобы достать target_id
                    move = CombatMoveDTO(**move_json)
                    # payload теперь объект, используем getattr
                    tid = getattr(move.payload, "target_id", None)
                    if tid:
                        covered_targets.add(normalize_actor_id(tid))
                except Exception:  # noqa: BLE001
                    pass

            # 3. Сравниваем и фильтруем мертвых из целей
            missing_targets_raw = list({normalize_actor_id(tid) for tid in my_targets} - covered_targets)
            # Фильтруем мертвых из списка целей
            missing_targets = [tid for tid in missing_targets_raw if str(tid) not in dead_set]

            if missing_targets:
                # Бот не покрыл все цели -> Ставим задачу с указанием целей
                tasks.append(AiTurnRequestDTO(session_id=session_id, bot_id=actor_id, missing_targets=missing_targets))

        return tasks

    def _harvest_instant(self, moves_map: dict[str, Any], meta: BattleMeta) -> tuple[list[CombatActionDTO], list[str]]:
        """Resolve item/instant intents into runnable action DTOs."""
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
                        raw_target = self._instant_target_instruction(move)
                        target_ids = self.target_resolver.resolve(cast("ActorIdLike", char_id), raw_target, meta)

                        # Записываем результат резолвинга в сам мув
                        move.targets = target_ids

                        # Создаем ОДИН Action на весь мув (с множеством целей)
                        # Используем cast для успокоения mypy
                        action_type = cast("Literal['exchange', 'item', 'instant', 'system']", strategy)
                        action = CombatActionDTO(action_type=action_type, move=move, is_forced=False)

                        actions.append(action)
                        to_delete.append(move_id)  # Удаляем мув после обработки

                    except Exception:  # noqa: BLE001
                        log.bind(strategy=strategy, move_id=move_id).exception("CollectorMoveParseFailed")

        return actions, to_delete

    @staticmethod
    def _instant_target_instruction(move: CombatMoveDTO) -> ActorIdLike | None:
        raw_target = getattr(move.payload, "target_id", None)
        ability_id = getattr(move.payload, "ability_id", None)
        if not ability_id:
            return raw_target

        entry = CombatCatalogIntegrator.get_ability_catalog_entry(str(ability_id))
        if entry is None:
            return raw_target
        ability = entry.technical
        target_count = max(1, int(getattr(ability, "target_count", 1) or 1))
        if str(ability.target) == "random_enemy" and target_count > 1:
            return f"random_enemy_{target_count}"
        if str(ability.target) == "all_enemies":
            return "all_enemies"
        if str(ability.target) == "self":
            return "self"
        return raw_target

    def _matchmake_exchange(
        self, moves_map: dict[str, Any], signal: CollectorSignalDTO | None = None
    ) -> tuple[list[CombatActionDTO], list[str]]:
        """Match paired exchange intents and synthesize forced timeout actions."""
        actions = []
        to_delete = []

        # Собираем пул всех exchange заявок и индекс для быстрого поиска
        # встречного намерения B -> A. Порядок pool отражает порядок,
        # доступный collector из moves_map; когда появится явный sequence,
        # его можно будет использовать вместо локального индекса.
        pool: list[tuple[int, CombatMoveDTO]] = []
        exchange_by_pair: dict[tuple[str, str], tuple[int, CombatMoveDTO]] = {}
        for _char_id, moves_data in moves_map.items():
            exchanges = moves_data.get("exchange", {})
            for _move_id, move_json in exchanges.items():
                try:
                    move = CombatMoveDTO(**move_json)
                    target_id = getattr(move.payload, "target_id", None)
                    if target_id is None:
                        continue
                    order = len(pool)
                    pool.append((order, move))
                    exchange_by_pair[(str(move.char_id), str(target_id))] = (order, move)
                except Exception:  # noqa: BLE001
                    pass

        matched_ids = set()
        ready_pairs: list[tuple[int, int, CombatActionDTO]] = []

        # 1. Normal Matchmaking
        for order_a, move_a in pool:
            if move_a.move_id in matched_ids:
                continue

            # payload теперь объект, используем getattr
            target_id = getattr(move_a.payload, "target_id", None)
            if not target_id:
                continue

            # Ищем ответный мув (B -> A) через индекс, без повторного перебора pool.
            partner_entry = exchange_by_pair.get((str(target_id), str(move_a.char_id)))
            if partner_entry is None:
                continue

            order_b, move_b = partner_entry
            if move_b.move_id == move_a.move_id or move_b.move_id in matched_ids:
                continue

            # Пара готова только когда пришли оба намерения; порядок очереди
            # задаем по более позднему из двух намерений, то есть по ответу.
            ready_order = max(order_a, order_b)
            action = CombatActionDTO(action_type="exchange", move=move_a, partner_move=move_b, is_forced=False)
            ready_pairs.append((ready_order, min(order_a, order_b), action))
            matched_ids.add(move_a.move_id)
            matched_ids.add(move_b.move_id)

        for _ready_order, _first_order, action in sorted(ready_pairs, key=lambda item: (item[0], item[1])):
            actions.append(action)
            to_delete.append(action.move.move_id)
            if action.partner_move:
                to_delete.append(action.partner_move.move_id)

        # 2. Force Attack Check (Timeout)
        if signal and signal.signal_type == "check_timeout" and signal.move_id:
            # Ищем мув, который вызвал таймаут
            # Если он еще в пуле (не сматчился выше) -> Force Attack

            force_candidates = []

            if signal.move_id == "batch":
                log.bind(
                    reason="unsafe_batch_timeout",
                    session_id=signal.session_id,
                    actor_id=signal.char_id,
                ).warning("CollectorTimeoutIgnored")
            else:
                # Specific move
                for _order, move in pool:
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
                log.bind(move_id=move.move_id).warning("CollectorForceAttackTriggered")

        return actions, to_delete
