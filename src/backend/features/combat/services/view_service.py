from __future__ import annotations

import contextlib
import json
import re
import time
from typing import Any, Literal

from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.shared.schemas.combat import (
    CombatAbilityBadgeDTO,
    CombatActionOptionDTO,
    CombatActorCardDTO,
    CombatActorVitalsDTO,
    CombatDashboardDTO,
    CombatDeltaDTO,
    CombatEffectBadgeDTO,
    CombatEventDTO,
    CombatExchangeStateDTO,
    CombatFeintOptionDTO,
    CombatLogActorRefDTO,
    CombatLogDTO,
    CombatLogTurnDTO,
)


class CombatViewService:
    """Maps combat Redis snapshots into frontend-facing read models."""

    def build_dashboard(
        self,
        *,
        session_id: str,
        viewer_id: int,
        meta: dict[str, Any],
        targets: dict[str, list[Any]],
        actors: dict[str, dict[str, Any] | None],
        raw_logs: list[str],
        raw_logs_by_turn: dict[str, list[str]] | None = None,
        total_logs: int | None = None,
        moves: dict[str, Any] | None = None,
    ) -> CombatDashboardDTO:
        moves = moves or {}
        now_ms = int(time.time() * 1000)
        dead_actor_ids = self._dead_actor_ids(meta)
        hero_raw = actors.get(str(viewer_id))
        if not hero_raw:
            raise ValueError(f"Actor {viewer_id} is not present in combat session {session_id}")

        hero = self._enrich_actor_card(
            self._map_actor(str(viewer_id), hero_raw, is_target=False, dead_actor_ids=dead_actor_ids),
            actor_id=str(viewer_id),
            targets=targets,
            moves=moves,
            now_ms=now_ms,
        )
        target = self._resolve_target(str(viewer_id), targets, actors, moves, dead_actor_ids, now_ms=now_ms)
        target_id = target.actor_id if target else None
        allies: list[CombatActorCardDTO] = []
        enemies: list[CombatActorCardDTO] = []

        for actor_id, actor_raw in actors.items():
            if actor_id == str(viewer_id) or not actor_raw:
                continue
            card = self._enrich_actor_card(
                self._map_actor(actor_id, actor_raw, is_target=actor_id == target_id, dead_actor_ids=dead_actor_ids),
                actor_id=actor_id,
                targets=targets,
                moves=moves,
                now_ms=now_ms,
            )
            if card.team == hero.team:
                allies.append(card)
            else:
                enemies.append(card)

        allies.sort(key=lambda actor: (actor.is_dead, actor.name))
        enemies.sort(key=lambda actor: (actor.is_dead, actor.name))
        winner_team = self._optional_str(meta.get("winner")) or self._inferred_winner_team(hero, allies, enemies)
        status = self._status(meta, hero, target, winner_team=winner_team)
        pending_action_count = self._pending_action_count(moves.get(str(viewer_id), {}))
        action_state = self._action_state(status, target=target, pending_action_count=pending_action_count)

        log_turns = self.parse_logs_by_turn(raw_logs_by_turn) if raw_logs_by_turn is not None else []
        log_events = self._flatten_turn_events(log_turns) if log_turns else self.parse_logs(raw_logs)
        exchange_state = self._exchange_state(
            viewer_id=str(viewer_id),
            status=status,
            action_state=action_state,
            target=target,
            targets=targets,
            actors=self._actor_cards_by_id(hero=hero, allies=allies, enemies=enemies),
            moves=moves,
            log_turns=log_turns,
            log_events=log_events,
        )

        return CombatDashboardDTO(
            session_id=session_id,
            turn_number=self._int(meta.get("step_counter")),
            status=status,
            phase=self._optional_str(meta.get("phase")) or action_state,
            battle_type=self._optional_str(meta.get("battle_type")),
            location_id=self._optional_str(meta.get("location_id")),
            personal_turn_number=self._optional_int(meta.get("personal_turn_number")) or hero.exchange_counter,
            round_size=self._optional_int(meta.get("round_size")) or self._round_size(targets, actors, dead_actor_ids),
            action_state=action_state,
            target_queue_size=hero.target_queue_size,
            pending_action_count=pending_action_count,
            hero=hero,
            target=target,
            allies=allies,
            enemies=enemies,
            active_effects=hero.active_effects,
            feints=hero.feints,
            available_actions=self._available_actions(status, target, hero, pending_action_count=pending_action_count),
            exchange_state=exchange_state,
            events_delta=CombatDeltaDTO(events=log_events, turns=log_turns),
            log_total=total_logs if total_logs is not None else len(raw_logs),
            winner_team=winner_team,
        )

    def build_logs(
        self,
        *,
        session_id: str,
        raw_logs: list[str],
        raw_logs_by_turn: dict[str, list[str]] | None = None,
        page: int,
        page_size: int,
        total: int,
    ) -> CombatLogDTO:
        turns = self.parse_logs_by_turn(raw_logs_by_turn) if raw_logs_by_turn is not None else []
        entries = self._flatten_turn_events(turns) if turns else self.parse_logs(raw_logs)
        return CombatLogDTO(
            session_id=session_id,
            entries=entries,
            turns=turns,
            total_turns=total,
            total=total,
            page=page,
            page_size=page_size,
        )

    @classmethod
    def parse_logs_by_turn(cls, raw_logs_by_turn: dict[str, list[str]]) -> list[CombatLogTurnDTO]:
        grouped: dict[int | None, list[CombatEventDTO]] = {}
        current_turn: int | None = None
        for raw_turn, raw_logs in sorted(raw_logs_by_turn.items(), key=lambda item: cls._turn_sort_key(item[0])):
            entries = cls.parse_logs(raw_logs)
            key_turn = cls._storage_turn_key(raw_turn)
            for entry in entries:
                event_turn = cls._event_turn(entry)
                if event_turn is not None:
                    current_turn = event_turn
                elif key_turn is not None and key_turn > 0:
                    current_turn = key_turn
                grouped.setdefault(current_turn, []).append(entry)
        return [
            CombatLogTurnDTO(
                global_turn=global_turn,
                title=f"Ход {global_turn}" if global_turn is not None else "Ход NO_DATA",
                entries=entries,
            )
            for global_turn, entries in sorted(
                grouped.items(),
                key=lambda item: item[0] if item[0] is not None else -1,
                reverse=True,
            )
        ]

    @staticmethod
    def _flatten_turn_events(turns: list[CombatLogTurnDTO]) -> list[CombatEventDTO]:
        return [event for turn in turns for event in turn.entries]

    @classmethod
    def parse_logs(cls, raw_logs: list[str]) -> list[CombatEventDTO]:
        events: list[CombatEventDTO] = []
        for raw in raw_logs:
            if isinstance(raw, bytes):
                raw = raw.decode()
            parsed: Any = raw
            if isinstance(raw, str):
                with contextlib.suppress(json.JSONDecodeError):
                    parsed = json.loads(raw)
            if isinstance(parsed, dict):
                text_raw = cls._optional_str(parsed.get("text"))
                extra = {k: v for k, v in parsed.items() if k not in {"type", "text", "timestamp", "tags", "data"}}
                if "global_turn" not in extra:
                    inferred_turn = cls._turn_from_text(text_raw)
                    if inferred_turn is not None:
                        extra["global_turn"] = inferred_turn
                data_raw = parsed.get("data")
                data = data_raw if isinstance(data_raw, dict) else dict(extra)
                events.append(
                    CombatEventDTO(
                        type=str(parsed.get("type") or "log"),
                        text=cls._strip_turn_prefix(text_raw),
                        timestamp=parsed.get("timestamp") if isinstance(parsed.get("timestamp"), int | float) else None,
                        tags=[str(tag) for tag in parsed.get("tags", []) if tag],
                        data=data,
                        **extra,
                    )
                )
            else:
                events.append(CombatEventDTO(text=cls._strip_turn_prefix(str(parsed))))
        return events

    def _resolve_target(
        self,
        viewer_id: str,
        targets: dict[str, list[Any]],
        actors: dict[str, dict[str, Any] | None],
        moves: dict[str, Any],
        dead_actor_ids: set[str],
        now_ms: int,
    ) -> CombatActorCardDTO | None:
        queue = targets.get(viewer_id)
        if not queue:
            return None
        for raw_target_id in queue:
            target_id = str(raw_target_id)
            target_raw = actors.get(target_id)
            if not target_raw:
                continue
            target = self._enrich_actor_card(
                self._map_actor(target_id, target_raw, is_target=True, dead_actor_ids=dead_actor_ids),
                actor_id=target_id,
                targets=targets,
                moves=moves,
                now_ms=now_ms,
            )
            if not target.is_dead:
                return target
        return None

    def _map_actor(
        self,
        actor_id: str,
        actor: dict[str, Any],
        *,
        is_target: bool,
        dead_actor_ids: set[str],
    ) -> CombatActorCardDTO:
        meta_raw = actor.get("meta")
        meta = meta_raw if isinstance(meta_raw, dict) else {}

        loadout_raw = actor.get("loadout")
        loadout = loadout_raw if isinstance(loadout_raw, dict) else {}

        statuses_raw = actor.get("statuses")
        statuses = statuses_raw if isinstance(statuses_raw, dict) else {}

        metrics_raw = actor.get("metrics")
        metrics = metrics_raw if isinstance(metrics_raw, dict) else {}

        tokens = self._visible_tokens(meta)
        source_raw = actor.get("source")
        source = source_raw if isinstance(source_raw, dict) else {}
        visual_raw = meta.get("visual") or source.get("visual")
        visual = visual_raw if isinstance(visual_raw, dict) else {}
        avatar_url = self._optional_str(meta.get("avatar_url")) or self._visual_image_url(visual)

        return CombatActorCardDTO(
            actor_id=str(meta.get("id") or actor_id),
            name=str(meta.get("name") or actor_id),
            actor_type=str(meta.get("type") or "unknown"),
            team=str(meta.get("team") or "neutral"),
            avatar_url=avatar_url,
            archetype=self._optional_str(meta.get("archetype")),
            role=self._optional_str(meta.get("role")),
            template_id=self._optional_str(meta.get("template_id")),
            tags=[str(tag) for tag in meta.get("tags", []) if tag] if isinstance(meta.get("tags"), list) else [],
            source=dict(source),
            visual=dict(visual),
            gear_score=self._optional_int(meta.get("gear_score")) or self._optional_int(metrics.get("gear_score")),
            power_score=self._optional_int(meta.get("power_score")) or self._optional_int(metrics.get("power_score")),
            is_ai=bool(meta.get("is_ai", False)),
            is_dead=actor_id in dead_actor_ids or bool(meta.get("is_dead", False)) or self._int(meta.get("hp")) <= 0,
            is_target=is_target,
            exchange_counter=self._int(meta.get("exchange_counter")),
            vitals=CombatActorVitalsDTO(
                hp_current=self._int(meta.get("hp")),
                hp_max=self._int(meta.get("max_hp")),
                energy_current=self._int(meta.get("en")),
                energy_max=self._int(meta.get("max_en")),
                stamina_current=self._int(meta.get("stamina")),
                stamina_max=self._int(meta.get("max_stamina")),
                tactics=self._int(meta.get("tactics")),
            ),
            weapon_type=self._weapon_type(loadout),
            quick_items=self._quick_items(loadout),
            known_abilities=[str(ability_id) for ability_id in loadout.get("known_abilities", []) if ability_id],
            tokens=tokens,
            active_effects=self._effects(statuses),
            active_abilities=self._abilities(statuses),
            feints=self._feints(meta),
        )

    def _enrich_actor_card(
        self,
        card: CombatActorCardDTO,
        *,
        actor_id: str,
        targets: dict[str, list[Any]],
        moves: dict[str, Any],
        now_ms: int,
    ) -> CombatActorCardDTO:
        commit_state = self._actor_commit_state(moves.get(actor_id, {}), now_ms=now_ms)
        return card.model_copy(
            update={
                "target_queue_size": len(targets.get(actor_id, [])),
                "pending_actions": self._pending_actions(moves.get(actor_id, {})),
                **commit_state,
            }
        )

    def _available_actions(
        self,
        status: str,
        target: CombatActorCardDTO | None,
        hero: CombatActorCardDTO,
        *,
        pending_action_count: int,
    ) -> list[CombatActionOptionDTO]:
        actions = [CombatActionOptionDTO(action="system", label="Обновить", enabled=True)]
        if status == "active" and target is not None and not target.is_dead and not hero.is_dead:
            has_pending = pending_action_count > 0
            actions.insert(
                0,
                CombatActionOptionDTO(
                    action="exchange",
                    label="Атака",
                    enabled=not has_pending,
                    target_id=target.actor_id,
                    feint_id=None,
                    ability_id=None,
                    catalog_ref="triggers",
                    reason="action_registered" if has_pending else None,
                ),
            )
            actions.extend(
                CombatActionOptionDTO(
                    action="instant",
                    label=ability_id,
                    enabled=not has_pending and self._ability_enabled(hero, ability_id),
                    target_id=self._ability_target_id(ability_id, target, hero),
                    ability_id=ability_id,
                    feint_id=None,
                    catalog_ref="abilities",
                    reason="action_registered" if has_pending else None,
                )
                for ability_id in hero.known_abilities
            )
        return actions

    def _exchange_state(
        self,
        *,
        viewer_id: str,
        status: str,
        action_state: str,
        target: CombatActorCardDTO | None,
        targets: dict[str, list[Any]],
        actors: dict[str, CombatActorCardDTO],
        moves: dict[str, Any],
        log_turns: list[CombatLogTurnDTO],
        log_events: list[CombatEventDTO],
    ) -> CombatExchangeStateDTO:
        latest = self._latest_exchange_from_logs(log_turns, log_events)
        if status == "finished":
            return latest.model_copy(
                update={"pair_status": "resolved", "opponent_response_state": "resolved", "title": "COMBAT COMPLETE"}
            )

        target_id = target.actor_id if target else self._first_target_id(targets.get(viewer_id))
        opponent_responded = bool(target_id and self._has_exchange_move(moves, str(target_id), viewer_id))

        if action_state == "TARGET_QUEUE_EMPTY":
            return latest.model_copy(
                update={
                    "pair_status": "no_target",
                    "opponent_response_state": "unknown",
                    "title": "NO ACTIVE EXCHANGE",
                    "summary_text": "Очередь целей пуста. Активного размена нет.",
                    "source": self._actor_ref_from_card(actors.get(viewer_id)),
                    "target": None,
                }
            )

        if action_state == "ACTION_LOCKED":
            pair_status = "ready_to_resolve" if opponent_responded else "waiting_response"
            response_state = "responded" if opponent_responded else "waiting"
            summary = (
                "Ответ противника получен. Размен ожидает обработки движком."
                if opponent_responded
                else "Ход выбран. Ожидаем встречное действие противника."
            )
            return latest.model_copy(
                update={
                    "pair_status": pair_status,
                    "opponent_response_state": response_state,
                    "title": "WAITING FOR RESPONSE" if not opponent_responded else "PAIR READY",
                    "summary_text": summary,
                    "source": self._actor_ref_from_card(actors.get(viewer_id)),
                    "target": self._actor_ref_from_card(actors.get(str(target_id))) if target_id else None,
                }
            )

        if opponent_responded:
            return latest.model_copy(
                update={
                    "pair_status": "open",
                    "opponent_response_state": "responded",
                    "title": "OPPONENT COMMITTED",
                    "summary_text": "Противник уже выбрал действие против вас. Ваш ответ закроет пару размена.",
                    "source": self._actor_ref_from_card(actors.get(str(target_id))) if target_id else None,
                    "target": self._actor_ref_from_card(actors.get(viewer_id)),
                }
            )

        return latest.model_copy(
            update={
                "pair_status": "open" if target is not None else "unknown",
                "opponent_response_state": "waiting" if target is not None else "unknown",
                "title": "LAST EXCHANGE" if latest.turn is not None else "COMBAT CONTACT",
                "source": latest.source or self._actor_ref_from_card(actors.get(viewer_id)),
                "target": latest.target or (self._actor_ref_from_card(target) if target else None),
            }
        )

    @classmethod
    def _latest_exchange_from_logs(
        cls,
        log_turns: list[CombatLogTurnDTO],
        log_events: list[CombatEventDTO],
    ) -> CombatExchangeStateDTO:
        if log_turns:
            turn = log_turns[0]
            entry = next((entry for entry in turn.entries if entry.text), None)
            if entry is not None:
                return CombatExchangeStateDTO(
                    pair_status="resolved",
                    opponent_response_state="resolved",
                    title=turn.title or "LAST EXCHANGE",
                    summary_text=entry.text or "Размен завершен.",
                    turn=turn.global_turn,
                    source=entry.source,
                    target=entry.target,
                    outcome=entry.outcome,
                    badges=entry.badges,
                )
        for entry in log_events:
            if entry.text:
                return CombatExchangeStateDTO(
                    pair_status="resolved",
                    opponent_response_state="resolved",
                    title=f"Ход {entry.global_turn}" if entry.global_turn is not None else "LAST EXCHANGE",
                    summary_text=entry.text,
                    turn=entry.global_turn,
                    source=entry.source,
                    target=entry.target,
                    outcome=entry.outcome,
                    badges=entry.badges,
                )
        return CombatExchangeStateDTO()

    @staticmethod
    def _first_target_id(queue: object) -> str | None:
        if isinstance(queue, list) and queue:
            return str(queue[0])
        return None

    @staticmethod
    def _actor_cards_by_id(
        *,
        hero: CombatActorCardDTO,
        allies: list[CombatActorCardDTO],
        enemies: list[CombatActorCardDTO],
    ) -> dict[str, CombatActorCardDTO]:
        return {actor.actor_id: actor for actor in [hero, *allies, *enemies]}

    @staticmethod
    def _has_exchange_move(moves: dict[str, Any], source_id: str, target_id: str) -> bool:
        actor_moves = moves.get(source_id)
        if not isinstance(actor_moves, dict):
            return False
        exchange_moves = actor_moves.get("exchange")
        if not isinstance(exchange_moves, dict):
            return False
        for move_json in exchange_moves.values():
            payload = move_json.get("payload") if isinstance(move_json, dict) else None
            if isinstance(payload, dict) and str(payload.get("target_id")) == str(target_id):
                return True
            target = getattr(getattr(move_json, "payload", None), "target_id", None)
            if target is not None and str(target) == str(target_id):
                return True
        return False

    @staticmethod
    def _actor_ref_from_card(actor: CombatActorCardDTO | None) -> CombatLogActorRefDTO | None:
        if actor is None:
            return None
        return CombatLogActorRefDTO(
            id=actor.actor_id,
            name=actor.name,
            team=actor.team,
            actor_type=actor.actor_type,
        )

    @staticmethod
    def _ability_enabled(hero: CombatActorCardDTO, ability_id: str) -> bool:
        entry = CombatCatalogIntegrator.get_ability_catalog_entry(ability_id)
        if entry is None:
            return False
        ability = entry.technical
        return (
            hero.vitals.energy_current >= ability.cost.energy
            and hero.vitals.hp_current >= ability.cost.hp
            and hero.tokens.get("gift", 0) >= ability.cost.gift_tokens
        )

    @staticmethod
    def _ability_target_id(
        ability_id: str,
        target: CombatActorCardDTO,
        hero: CombatActorCardDTO,
    ) -> str | None:
        entry = CombatCatalogIntegrator.get_ability_catalog_entry(ability_id)
        if entry is None:
            return target.actor_id
        ability = entry.technical
        if ability.target == TargetType.SELF:
            return hero.actor_id
        if ability.target in {TargetType.ALL_ENEMIES, TargetType.ALL_ALLIES}:
            return None
        return target.actor_id

    @staticmethod
    def _status(
        meta: dict[str, Any],
        hero: CombatActorCardDTO,
        target: CombatActorCardDTO | None,
        *,
        winner_team: str | None = None,
    ) -> Literal["active", "waiting", "finished", "spectating"]:
        if str(meta.get("active", "1")) == "0" or meta.get("winner") or winner_team:
            return "finished"
        if hero.is_dead:
            return "spectating"
        if target is None:
            return "waiting"
        return "active"

    @staticmethod
    def _inferred_winner_team(
        hero: CombatActorCardDTO,
        allies: list[CombatActorCardDTO],
        enemies: list[CombatActorCardDTO],
    ) -> str | None:
        if any(not actor.is_dead for actor in [hero, *allies]):
            return None
        alive_enemy_teams = sorted({actor.team for actor in enemies if not actor.is_dead and actor.team})
        if len(alive_enemy_teams) == 1:
            return alive_enemy_teams[0]
        return None

    @staticmethod
    def _action_state(
        status: str,
        *,
        target: CombatActorCardDTO | None,
        pending_action_count: int,
    ) -> str:
        if status == "finished":
            return "FINISHED"
        if status == "spectating":
            return "SPECTATING"
        if pending_action_count:
            return "ACTION_LOCKED"
        if target is None:
            return "TARGET_QUEUE_EMPTY"
        return "ACTION_READY"

    @staticmethod
    def _round_size(
        targets: dict[str, list[Any]],
        actors: dict[str, dict[str, Any] | None],
        dead_actor_ids: set[str],
    ) -> int:
        active_actor_ids = {actor_id for actor_id, actor in actors.items() if actor and actor_id not in dead_actor_ids}
        return sum(
            1
            for actor_id, queue in targets.items()
            if actor_id in active_actor_ids
            for target_id in queue
            if str(target_id) not in dead_actor_ids
        )

    @staticmethod
    def _weapon_type(loadout: dict[str, Any]) -> str | None:
        layout_raw = loadout.get("layout") or loadout.get("equipment_layout")
        layout = layout_raw if isinstance(layout_raw, dict) else {}
        return CombatViewService._optional_str(
            layout.get("main_hand") or layout.get("weapon") or layout.get("slot_weapon")
        )

    @staticmethod
    def _quick_items(loadout: dict[str, Any]) -> list[dict[str, Any]]:
        belt_raw = loadout.get("belt")
        belt = belt_raw if isinstance(belt_raw, list) else []
        return [dict(item) for item in belt if isinstance(item, dict)]

    @staticmethod
    def _effects(statuses: dict[str, Any]) -> list[CombatEffectBadgeDTO]:
        result = []
        effects_raw = statuses.get("effects")
        effects_list = effects_raw if isinstance(effects_raw, list) else []
        for item in effects_list:
            if not isinstance(item, dict) or not item.get("effect_id"):
                continue
            impact_raw = item.get("impact")
            impact = impact_raw if isinstance(impact_raw, dict) else {}
            result.append(
                CombatEffectBadgeDTO(
                    uid=CombatViewService._optional_str(item.get("uid")),
                    effect_id=str(item["effect_id"]),
                    expires_at_exchange=CombatViewService._optional_int(item.get("expire_at_exchange")),
                    impact=impact,
                    **CombatViewService._effect_catalog_badge_fields(str(item["effect_id"])),
                )
            )
        return result

    @staticmethod
    def _effect_catalog_badge_fields(effect_id: str) -> dict[str, str | None]:
        entry = CombatCatalogIntegrator.get_effect_catalog_entry(effect_id)
        if entry is None:
            return {}
        description = entry.descriptive.variants.get(entry.descriptive.default_taxonomy)
        if description is None:
            return {}
        return {
            "title": description.display_name,
            "description": description.tooltip or description.short_description,
            "duration_label": CombatViewService._reactive_effect_duration_label(
                list(entry.technical.react_on_outcomes),
                consume_on_reaction=entry.technical.consume_on_reaction,
            ),
        }

    @staticmethod
    def _reactive_effect_duration_label(outcomes: list[str], *, consume_on_reaction: bool) -> str | None:
        if not consume_on_reaction or not outcomes:
            return None
        normalized = {str(outcome).lower() for outcome in outcomes}
        if normalized == {"parry"}:
            return "до следующего парирования"
        if normalized == {"dodge"}:
            return "до следующего уворота"
        if normalized <= {"hit", "crit"}:
            return "до следующего попадания"
        if normalized == {"block"}:
            return "до следующего блока"
        return "до следующего события"

    @staticmethod
    def _abilities(statuses: dict[str, Any]) -> list[CombatAbilityBadgeDTO]:
        result = []
        abilities_raw = statuses.get("abilities")
        abilities_list = abilities_raw if isinstance(abilities_raw, list) else []
        for item in abilities_list:
            if not isinstance(item, dict) or not item.get("ability_id"):
                continue
            impact_raw = item.get("impact")
            impact = impact_raw if isinstance(impact_raw, dict) else {}
            result.append(
                CombatAbilityBadgeDTO(
                    uid=CombatViewService._optional_str(item.get("uid")),
                    ability_id=str(item["ability_id"]),
                    expires_at_exchange=CombatViewService._optional_int(item.get("expire_at_exchange")),
                    impact=impact,
                )
            )
        return result

    @staticmethod
    def _feints(meta: dict[str, Any]) -> list[CombatFeintOptionDTO]:
        feints_raw = meta.get("feints")
        feints = feints_raw if isinstance(feints_raw, dict) else {}
        hand_raw = feints.get("hand")
        hand = hand_raw if isinstance(hand_raw, dict) else {}
        pinned = str(feints.get("pinned")) if feints.get("pinned") is not None else None
        return [
            CombatFeintOptionDTO(
                feint_id=str(feint_id),
                cost={str(k): CombatViewService._int(v) for k, v in cost.items()} if isinstance(cost, dict) else {},
                pinned=str(feint_id) == pinned,
            )
            for feint_id, cost in hand.items()
        ]

    @classmethod
    def _visible_tokens(cls, meta: dict[str, Any]) -> dict[str, int]:
        tokens_raw = meta.get("tokens")
        tokens_source = tokens_raw if isinstance(tokens_raw, dict) else {}
        tokens = {str(k): cls._int(v) for k, v in tokens_source.items()}

        feints_raw = meta.get("feints")
        feints = feints_raw if isinstance(feints_raw, dict) else {}
        hand_raw = feints.get("hand")
        hand = hand_raw if isinstance(hand_raw, dict) else {}
        for cost in hand.values():
            if not isinstance(cost, dict):
                continue
            for token, amount in cost.items():
                key = str(token)
                tokens[key] = tokens.get(key, 0) + cls._int(amount)
        return tokens

    @classmethod
    def _visual_image_url(cls, visual: dict[str, Any]) -> str | None:
        for key in ("image_url", "generated_image_url", "fallback_image_url"):
            url = cls._optional_str(visual.get(key))
            if url:
                return url
        return None

    @staticmethod
    def _pending_actions(moves: Any) -> dict[str, int]:
        moves_map = moves if isinstance(moves, dict) else {}
        result: dict[str, int] = {}
        for strategy, values in moves_map.items():
            if isinstance(values, dict):
                result[str(strategy)] = len(values)
        return result

    @classmethod
    def _pending_action_count(cls, moves: Any) -> int:
        return sum(cls._pending_actions(moves).values())

    @classmethod
    def _actor_commit_state(cls, moves: Any, *, now_ms: int) -> dict[str, Any]:
        pending_moves = cls._pending_move_payloads(moves)
        if not pending_moves:
            return {
                "committed": False,
                "commit_state": "idle",
                "timeout_total_ms": None,
                "remaining_ms": None,
                "force_attack_at_ms": None,
            }

        deadline_move = min(
            pending_moves,
            key=lambda move: cls._optional_int(cls._move_field(move, "force_attack_at_ms")) or 2**63 - 1,
        )
        timeout_total_ms = cls._optional_int(cls._move_field(deadline_move, "timeout_ms"))
        force_attack_at_ms = cls._optional_int(cls._move_field(deadline_move, "force_attack_at_ms"))
        remaining_ms = max(0, force_attack_at_ms - now_ms) if force_attack_at_ms is not None else None

        commit_state = "committed"
        if remaining_ms is not None and timeout_total_ms:
            if remaining_ms <= 10_000:
                commit_state = "timeout_warning"
            elif remaining_ms <= timeout_total_ms / 2:
                commit_state = "half_time"

        return {
            "committed": True,
            "commit_state": commit_state,
            "timeout_total_ms": timeout_total_ms,
            "remaining_ms": remaining_ms,
            "force_attack_at_ms": force_attack_at_ms,
        }

    @classmethod
    def _pending_move_payloads(cls, moves: Any) -> list[Any]:
        moves_map = moves if isinstance(moves, dict) else {}
        result: list[Any] = []
        for values in moves_map.values():
            if isinstance(values, dict):
                result.extend(values.values())
        return result

    @staticmethod
    def _move_field(move: Any, field: str) -> Any:
        if isinstance(move, dict):
            return move.get(field)
        return getattr(move, field, None)

    @staticmethod
    def _dead_actor_ids(meta: dict[str, Any]) -> set[str]:
        dead_raw = meta.get("dead_actors")
        dead = CombatViewService._decode_json_field(dead_raw, default=[])
        return {str(actor_id) for actor_id in dead} if isinstance(dead, list) else set()

    @staticmethod
    def _decode_json_field(value: Any, *, default: Any) -> Any:
        if value in (None, ""):
            return default
        if isinstance(value, dict | list):
            return value
        with contextlib.suppress(json.JSONDecodeError):
            return json.loads(str(value))
        return default

    @staticmethod
    def _int(value: Any) -> int:
        with contextlib.suppress(TypeError, ValueError):
            return int(value)
        return 0

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        with contextlib.suppress(TypeError, ValueError):
            return int(value)
        if value not in (None, ""):
            match = re.search(r"\d+", str(value))
            if match:
                with contextlib.suppress(ValueError):
                    return int(match.group(0))
        return None

    @staticmethod
    def _turn_sort_key(turn: str) -> tuple[int, str]:
        numeric = CombatViewService._optional_int(turn)
        if numeric is not None:
            return (numeric, str(turn))
        return (0, str(turn))

    @classmethod
    def _event_turn(cls, entry: CombatEventDTO) -> int | None:
        turn = cls._optional_int(getattr(entry, "global_turn", None))
        if turn is None:
            turn = cls._optional_int(entry.data.get("global_turn"))
        if turn is None and entry.text:
            turn = cls._turn_from_text(entry.text)
        return turn

    @staticmethod
    def _strip_turn_prefix(text: str | None) -> str | None:
        if text is None:
            return None
        return re.sub(r"^\s*Ход\s+\d+\.\s*", "", text, count=1, flags=re.IGNORECASE)

    @classmethod
    def _turn_from_text(cls, text: str | None) -> int | None:
        if not text:
            return None
        match = re.search(r"\bХод\s+(\d+)\b", text, re.IGNORECASE)
        return cls._optional_int(match.group(1)) if match else None

    @classmethod
    def _storage_turn_key(cls, raw_turn: Any) -> int | None:
        if raw_turn in (None, ""):
            return None
        text = str(raw_turn)
        if re.fullmatch(r"(?:global_turn|turn)?[:_-]?\d+", text):
            return cls._optional_int(text)
        return None

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value in (None, ""):
            return None
        return str(value)
