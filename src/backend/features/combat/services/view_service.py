from __future__ import annotations

import contextlib
import json
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
    CombatFeintOptionDTO,
    CombatLogDTO,
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
        total_logs: int | None = None,
        moves: dict[str, Any] | None = None,
    ) -> CombatDashboardDTO:
        moves = moves or {}
        dead_actor_ids = self._dead_actor_ids(meta)
        hero_raw = actors.get(str(viewer_id))
        if not hero_raw:
            raise ValueError(f"Actor {viewer_id} is not present in combat session {session_id}")

        hero = self._enrich_actor_card(
            self._map_actor(str(viewer_id), hero_raw, is_target=False, dead_actor_ids=dead_actor_ids),
            actor_id=str(viewer_id),
            targets=targets,
            moves=moves,
        )
        target = self._resolve_target(str(viewer_id), targets, actors, moves, dead_actor_ids)
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
            )
            if card.team == hero.team:
                allies.append(card)
            else:
                enemies.append(card)

        allies.sort(key=lambda actor: (actor.is_dead, actor.name))
        enemies.sort(key=lambda actor: (actor.is_dead, actor.name))
        status = self._status(meta, hero, target)
        pending_action_count = self._pending_action_count(moves.get(str(viewer_id), {}))
        action_state = self._action_state(status, target=target, pending_action_count=pending_action_count)

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
            events_delta=CombatDeltaDTO(events=self.parse_logs(raw_logs)),
            log_total=total_logs if total_logs is not None else len(raw_logs),
            winner_team=self._optional_str(meta.get("winner")),
        )

    def build_logs(
        self,
        *,
        session_id: str,
        raw_logs: list[str],
        page: int,
        page_size: int,
        total: int,
    ) -> CombatLogDTO:
        return CombatLogDTO(
            session_id=session_id,
            entries=self.parse_logs(raw_logs),
            page=page,
            page_size=page_size,
            total=total,
        )

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
                data_raw = parsed.get("data")
                data = (
                    data_raw
                    if isinstance(data_raw, dict)
                    else {k: v for k, v in parsed.items() if k not in {"type", "text", "timestamp", "tags"}}
                )
                events.append(
                    CombatEventDTO(
                        type=str(parsed.get("type") or "log"),
                        text=cls._optional_str(parsed.get("text")),
                        timestamp=parsed.get("timestamp") if isinstance(parsed.get("timestamp"), int | float) else None,
                        tags=[str(tag) for tag in parsed.get("tags", []) if tag],
                        data=data,
                    )
                )
            else:
                events.append(CombatEventDTO(text=str(parsed)))
        return events

    def _resolve_target(
        self,
        viewer_id: str,
        targets: dict[str, list[Any]],
        actors: dict[str, dict[str, Any] | None],
        moves: dict[str, Any],
        dead_actor_ids: set[str],
    ) -> CombatActorCardDTO | None:
        queue = targets.get(viewer_id)
        if not queue:
            return None
        target_id = str(queue[0])
        target_raw = actors.get(target_id)
        if not target_raw:
            return None
        return self._enrich_actor_card(
            self._map_actor(target_id, target_raw, is_target=True, dead_actor_ids=dead_actor_ids),
            actor_id=target_id,
            targets=targets,
            moves=moves,
        )

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

        tokens_raw = meta.get("tokens")
        tokens = tokens_raw if isinstance(tokens_raw, dict) else {}

        return CombatActorCardDTO(
            actor_id=str(meta.get("id") or actor_id),
            name=str(meta.get("name") or actor_id),
            actor_type=str(meta.get("type") or "unknown"),
            team=str(meta.get("team") or "neutral"),
            avatar_url=self._optional_str(meta.get("avatar_url")),
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
                tactics=self._int(meta.get("tactics")),
            ),
            weapon_type=self._weapon_type(loadout),
            quick_items=self._quick_items(loadout),
            known_abilities=[str(ability_id) for ability_id in loadout.get("known_abilities", []) if ability_id],
            tokens={str(k): self._int(v) for k, v in tokens.items()},
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
    ) -> CombatActorCardDTO:
        return card.model_copy(
            update={
                "target_queue_size": len(targets.get(actor_id, [])),
                "pending_actions": self._pending_actions(moves.get(actor_id, {})),
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
        actions = [
            CombatActionOptionDTO(action="system", label="Обновить", enabled=True),
            CombatActionOptionDTO(action="system", label="Сбежать", enabled=not hero.is_dead),
        ]
        if status == "active" and target is not None and not hero.is_dead:
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

    @staticmethod
    def _ability_enabled(hero: CombatActorCardDTO, ability_id: str) -> bool:
        ability = CombatCatalogIntegrator.get_ability(ability_id)
        if ability is None:
            return False
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
        ability = CombatCatalogIntegrator.get_ability(ability_id)
        if ability is None:
            return target.actor_id
        if ability.target == TargetType.SELF:
            return hero.actor_id
        if ability.target in {TargetType.ALL_ENEMIES, TargetType.ALL_ALLIES}:
            return None
        return target.actor_id

    @staticmethod
    def _status(
        meta: dict[str, Any], hero: CombatActorCardDTO, target: CombatActorCardDTO | None
    ) -> Literal["active", "waiting", "finished", "spectating"]:
        if str(meta.get("active", "1")) == "0" or meta.get("winner"):
            return "finished"
        if hero.is_dead:
            return "spectating"
        if target is None:
            return "waiting"
        return "active"

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
        return sum(len(queue) for actor_id, queue in targets.items() if actor_id in active_actor_ids)

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
                )
            )
        return result

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
        return [
            CombatFeintOptionDTO(
                feint_id=str(feint_id),
                cost={str(k): CombatViewService._int(v) for k, v in cost.items()} if isinstance(cost, dict) else {},
            )
            for feint_id, cost in hand.items()
        ]

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
        return None

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value in (None, ""):
            return None
        return str(value)
