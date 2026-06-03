from __future__ import annotations

import contextlib
import json
import math
import re
import time
from typing import Any, Literal

from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.monsters.resources.visuals import version_generated_asset_url
from src.shared.schemas.combat import (
    CombatAbilityBadgeDTO,
    CombatActionOptionDTO,
    CombatActorCardDTO,
    CombatActorStatSheetDTO,
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
    CombatStatSectionDTO,
    CombatStatValueDTO,
)

EMPTY_ASSET_URL_SENTINELS = {"none", "null", "undefined"}

STAT_SHEET_SECTION_KEYS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("attributes", "ATTRIBUTES", ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")),
    (
        "vitals",
        "VITALS",
        ("hp", "hp_regen", "en", "en_regen", "stamina", "stamina_regen", "resource_cost_reduction", "initiative"),
    ),
    (
        "main_hand",
        "MAIN HAND",
        (
            "main_hand_damage_base",
            "main_hand_damage_spread",
            "main_hand_damage_bonus",
            "main_hand_armor_penetration_pct",
            "main_hand_armor_ignore_chance",
            "main_hand_accuracy",
            "main_hand_crit_chance",
            "main_hand_crit_cap",
        ),
    ),
    (
        "off_hand",
        "OFF HAND",
        (
            "off_hand_damage_base",
            "off_hand_damage_spread",
            "off_hand_damage_bonus",
            "off_hand_armor_penetration_pct",
            "off_hand_armor_ignore_chance",
            "off_hand_accuracy",
            "off_hand_crit_chance",
            "off_hand_crit_cap",
        ),
    ),
    (
        "item",
        "ITEM",
        (
            "item_damage_base",
            "item_damage_spread",
            "item_damage_bonus",
            "item_armor_penetration_pct",
            "item_armor_ignore_chance",
            "item_accuracy",
            "item_crit_chance",
            "item_crit_cap",
        ),
    ),
    (
        "physical",
        "PHYSICAL",
        (
            "physical_damage",
            "physical_damage_bonus",
            "accuracy",
            "physical_suppression",
            "armor_penetration_pct",
            "armor_penetration_flat",
            "armor_ignore_chance",
            "crit_chance",
            "crit_power",
        ),
    ),
    (
        "magical",
        "MAGICAL",
        (
            "magical_damage",
            "magical_damage_spread",
            "magical_damage_bonus",
            "magical_accuracy",
            "magical_damage_power",
            "magical_penetration",
            "spell_land_chance",
            "magical_crit_chance",
            "magical_crit_cap",
        ),
    ),
    (
        "defense",
        "DEFENSE",
        ("evasion", "dodge_cap", "anti_dodge_chance", "parry", "parry_cap", "block", "shield_block_cap"),
    ),
    (
        "mitigation",
        "MITIGATION",
        (
            "physical_resistance",
            "magic_resist",
            "resistance_cap",
            "armor",
            "shield_guard_power",
            "shield_absorb_ratio",
            "shield_reflect_ratio",
        ),
    ),
    (
        "elemental",
        "ELEMENTAL",
        (
            "fire_damage_bonus",
            "fire_resistance",
            "water_damage_bonus",
            "water_resistance",
            "air_damage_bonus",
            "air_resistance",
            "earth_damage_bonus",
            "earth_resistance",
            "light_damage_bonus",
            "light_resistance",
            "dark_damage_bonus",
            "dark_resistance",
            "arcane_damage_bonus",
            "arcane_resistance",
            "nature_damage_bonus",
            "nature_resistance",
        ),
    ),
    (
        "status",
        "STATUS",
        (
            "control_chance_bonus",
            "control_resistance",
            "mental_resistance",
            "debuff_avoidance",
            "shock_resistance",
            "poison_damage_bonus",
            "poison_resistance",
            "poison_efficiency",
            "bleed_damage_bonus",
            "bleed_resistance",
        ),
    ),
    (
        "special",
        "SPECIAL",
        (
            "counter_attack_chance",
            "counter_attack_cap",
            "vampiric_power",
            "vampiric_trigger_chance",
            "vampiric_trigger_cap",
            "healing_power",
            "received_healing_bonus",
            "pet_efficiency_mult",
            "damage_mult",
            "thorns_damage_flat",
            "hand_size",
        ),
    ),
    (
        "environment",
        "ENVIRONMENT",
        (
            "environment_cold_resistance",
            "environment_heat_resistance",
            "environment_gravity_resistance",
            "environment_bio_resistance",
        ),
    ),
)

STAT_SHEET_SPEED_KEYS = frozenset({"attack_speed", "cast_speed", "movement_speed"})

_ATTRIBUTE_DISPLAY_KEYS: tuple[str, ...] = (
    "strength",
    "agility",
    "endurance",
    "intellect",
    "memory",
    "mental",
    "perception",
    "projection",
    "prediction",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)

_OFFENSE_WEAPON_SLOTS: tuple[tuple[str, str], ...] = (
    ("main_hand", "MH"),
    ("off_hand", "OH"),
    ("item", "ITEM"),
)

_STATUS_RESIST_ROWS: tuple[tuple[str, str], ...] = (
    ("control_resistance", "CONTROL RES"),
    ("mental_resistance", "MENTAL RES"),
    ("debuff_avoidance", "DEBUFF AVOID"),
    ("shock_resistance", "SHOCK RES"),
    ("bleed_resistance", "BLEED RES"),
    ("bleed_damage_bonus", "BLEED BONUS"),
    ("poison_resistance", "POISON RES"),
    ("poison_damage_bonus", "POISON BONUS"),
    ("poison_efficiency", "POISON EFF"),
    ("control_chance_bonus", "CONTROL BONUS"),
)

_ELEMENTAL_NAMES: tuple[str, ...] = (
    "fire",
    "water",
    "air",
    "earth",
    "light",
    "dark",
    "arcane",
    "nature",
)

_STAT_SHEET_BASE_HIT_CHANCE = 0.60

_CAP_ROWS: tuple[tuple[str, str], ...] = (
    ("dodge_cap", "EVASION CAP"),
    ("parry_cap", "PARRY CAP"),
    ("shield_block_cap", "BLOCK CAP"),
    ("resistance_cap", "RESIST CAP"),
    ("main_hand_crit_cap", "MH CRIT CAP"),
    ("off_hand_crit_cap", "OH CRIT CAP"),
    ("item_crit_cap", "ITEM CRIT CAP"),
    ("magical_crit_cap", "MAG CRIT CAP"),
    ("counter_attack_cap", "COUNTER CAP"),
    ("vampiric_trigger_cap", "VAMP CAP"),
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
            available_actions=self._available_actions(
                status,
                target,
                hero,
                pending_action_count=pending_action_count,
                action_state=action_state,
            ),
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
        avatar_url = self._avatar_image_url(meta.get("avatar_url"), visual=visual) or self._visual_image_url(visual)

        actor_name = str(meta.get("name") or actor_id)
        return CombatActorCardDTO(
            actor_id=str(meta.get("id") or actor_id),
            name=actor_name,
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
            stat_sheet=self._stat_sheet(actor, actor_id=str(meta.get("id") or actor_id), actor_name=actor_name),
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
        action_state: str,
    ) -> list[CombatActionOptionDTO]:
        actions = [CombatActionOptionDTO(action="system", label="Обновить", enabled=True)]
        if status == "active" and target is not None and not target.is_dead and not hero.is_dead:
            enabled = action_state in ("ACTION_READY", "EXCHANGE_PENDING_WITH_TARGETS")
            actions.insert(
                0,
                CombatActionOptionDTO(
                    action="exchange",
                    label="Атака",
                    enabled=enabled,
                    target_id=target.actor_id,
                    feint_id=None,
                    ability_id=None,
                    catalog_ref="triggers",
                    reason="action_registered" if not enabled else None,
                ),
            )
            actions.extend(
                CombatActionOptionDTO(
                    action="instant",
                    label=ability_id,
                    enabled=enabled and self._ability_enabled(hero, ability_id),
                    target_id=self._ability_target_id(ability_id, target, hero),
                    ability_id=ability_id,
                    feint_id=None,
                    catalog_ref="abilities",
                    reason="action_registered" if not enabled else None,
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
        if not target_id:
            viewer_moves = moves.get(viewer_id) or moves.get(str(viewer_id))
            if isinstance(viewer_moves, dict):
                exchange_moves = viewer_moves.get("exchange")
                if isinstance(exchange_moves, dict):
                    for move_json in exchange_moves.values():
                        payload = move_json.get("payload") if isinstance(move_json, dict) else None
                        if isinstance(payload, dict) and payload.get("target_id"):
                            target_id = str(payload.get("target_id"))
                            break
                        t = getattr(getattr(move_json, "payload", None), "target_id", None)
                        if t is not None:
                            target_id = str(t)
                            break
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

        if action_state == "WAITING_FOR_RESPONSES":
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
            and all(hero.tokens.get(token, 0) >= amount for token, amount in ability.cost.tokens.items())
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
        if target is not None:
            if pending_action_count > 0:
                return "EXCHANGE_PENDING_WITH_TARGETS"
            return "ACTION_READY"
        if pending_action_count > 0:
            return "WAITING_FOR_RESPONSES"
        return "TARGET_QUEUE_EMPTY"

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

    @classmethod
    def _stat_sheet(cls, actor: dict[str, Any], *, actor_id: str, actor_name: str) -> CombatActorStatSheetDTO | None:
        values = cls._stat_sheet_values(actor)
        if not values:
            return None

        sections: list[CombatStatSectionDTO] = []

        offense_items = cls._offense_items(values)
        if offense_items:
            sections.append(CombatStatSectionDTO(key="offense", label="OFFENSE", items=offense_items))

        defense_items = cls._defense_items(values)
        if defense_items:
            sections.append(CombatStatSectionDTO(key="defense", label="DEFENSE", items=defense_items))

        vitals_items = cls._vitals_regen_items(values)
        if vitals_items:
            sections.append(CombatStatSectionDTO(key="vitals", label="VITALS", items=vitals_items))

        status_items = cls._status_resist_items(values)
        if status_items:
            sections.append(CombatStatSectionDTO(key="status", label="STATUS", items=status_items))

        elemental_items = cls._elemental_items(values)
        if elemental_items:
            sections.append(CombatStatSectionDTO(key="elemental", label="ELEMENTAL", items=elemental_items))

        caps_items = cls._caps_items(values)
        if caps_items:
            sections.append(CombatStatSectionDTO(key="caps", label="CAPS", items=caps_items))

        attr_items = [cls._stat_item_raw(k, k.upper(), values[k]) for k in _ATTRIBUTE_DISPLAY_KEYS if values.get(k)]
        if attr_items:
            sections.append(CombatStatSectionDTO(key="attributes", label="ATTRIBUTES", items=attr_items))

        total_count = sum(len(s.items) for s in sections)
        if total_count == 0:
            return None
        return CombatActorStatSheetDTO(actor_id=actor_id, name=actor_name, sections=sections, total_count=total_count)

    @classmethod
    def _stat_sheet_values(cls, actor: dict[str, Any]) -> dict[str, float | int]:
        values: dict[str, float | int] = {}
        stats_raw = actor.get("stats")
        stats = stats_raw if isinstance(stats_raw, dict) else {}

        mods_raw = stats.get("mods")
        if isinstance(mods_raw, dict) and mods_raw:
            values.update(cls._numeric_nonzero_values(mods_raw))
        elif stats:
            values.update(
                cls._numeric_nonzero_values(
                    {key: value for key, value in stats.items() if key not in {"skills", "calculated_at"}}
                )
            )

        raw = actor.get("raw")
        raw_data = raw if isinstance(raw, dict) else {}
        raw_attributes = raw_data.get("attributes")
        calculated: dict[str, Any] = {}
        if isinstance(raw_attributes, dict) and raw_attributes:
            try:
                calculated, _ = StatsWaterfallCalculator.calculate_waterfall(raw_data)
            except Exception:  # noqa: BLE001
                calculated = {}
            if not values:
                values.update(cls._numeric_nonzero_values(calculated))
            for key in raw_attributes:
                numeric = cls._numeric_value(calculated.get(key))
                if numeric is not None and numeric != 0:
                    values[str(key)] = numeric

        return {key: value for key, value in values.items() if key not in STAT_SHEET_SPEED_KEYS}

    @staticmethod
    def _stat_sheet_attribute_keys(actor: dict[str, Any]) -> tuple[str, ...]:
        raw = actor.get("raw")
        raw_data = raw if isinstance(raw, dict) else {}
        raw_attributes = raw_data.get("attributes")
        if not isinstance(raw_attributes, dict):
            return ()
        known = set(STAT_SHEET_SECTION_KEYS[0][2])
        return tuple(str(key) for key in raw_attributes if str(key) not in known)

    @classmethod
    def _numeric_nonzero_values(cls, values: dict[str, Any]) -> dict[str, float | int]:
        result: dict[str, float | int] = {}
        for key, value in values.items():
            numeric = cls._numeric_value(value)
            if numeric is None or numeric == 0:
                continue
            result[str(key)] = numeric
        return result

    @staticmethod
    def _numeric_value(value: Any) -> float | int | None:
        if isinstance(value, bool) or value in (None, ""):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value) if value.is_integer() else value
        with contextlib.suppress(TypeError, ValueError):
            parsed = float(value)
            return int(parsed) if parsed.is_integer() else parsed
        return None

    @staticmethod
    def _stat_value_item(key: str, value: float | int) -> CombatStatValueDTO:
        return CombatStatValueDTO(
            key=key,
            label=key.replace("_", " ").upper(),
            value=value,
            value_text=CombatViewService._stat_value_text(value),
        )

    @staticmethod
    def _stat_value_text(value: float | int) -> str:
        if isinstance(value, int):
            return str(value)
        rounded = round(value, 4)
        return str(int(rounded)) if rounded.is_integer() else f"{rounded:g}"

    @classmethod
    def _offense_items(cls, values: dict[str, float | int]) -> list[CombatStatValueDTO]:
        items: list[CombatStatValueDTO] = []
        phys_bonus_pct = float(values.get("physical_damage_bonus") or 0)
        global_acc = float(values.get("accuracy") or 0)
        global_crit = float(values.get("crit_chance") or 0)
        global_pen = float(values.get("armor_penetration_pct") or 0)
        anti_dodge = float(values.get("anti_dodge_chance") or 0)

        # Aggregate armor pen across all weapon slots + global
        total_pen = global_pen

        for prefix, hand in _OFFENSE_WEAPON_SLOTS:
            base = float(values.get(f"{prefix}_damage_base") or 0)
            if not base:
                continue
            spread = float(values.get(f"{prefix}_damage_spread") or 0.1)
            min_d = max(0.0, base * (1.0 - spread))
            max_d = max(0.0, base * (1.0 + spread))
            items.append(
                CombatStatValueDTO(
                    key=f"{prefix}_damage",
                    label=f"{hand} DAMAGE",
                    value=base,
                    value_text=f"{cls._round_display(min_d)} — {cls._round_display(max_d)}",
                    tooltip=cls._damage_breakdown_tooltip(values, prefix, base=base, spread=spread),
                )
            )

            wpn_acc = float(values.get(f"{prefix}_accuracy") or 0)
            total_acc = round((_STAT_SHEET_BASE_HIT_CHANCE + wpn_acc + global_acc) * 100)
            items.append(
                CombatStatValueDTO(
                    key=f"{prefix}_accuracy",
                    label=f"{hand} ACCURACY",
                    value=total_acc,
                    value_text=f"{total_acc}%",
                )
            )

            wpn_crit = float(values.get(f"{prefix}_crit_chance") or 0)
            total_crit = round((wpn_crit + global_crit) * 100)
            if total_crit:
                items.append(
                    CombatStatValueDTO(
                        key=f"{prefix}_crit_chance",
                        label=f"{hand} CRIT",
                        value=total_crit,
                        value_text=f"{total_crit}%",
                    )
                )

            total_pen += float(values.get(f"{prefix}_armor_penetration_pct") or 0)

        if phys_bonus_pct:
            items.append(cls._stat_item_pct("physical_damage_bonus", "DMG BONUS", phys_bonus_pct))
        if anti_dodge:
            items.append(cls._stat_item_pct("anti_dodge_chance", "ANTI-DODGE", anti_dodge))
        if total_pen:
            items.append(cls._stat_item_pct("armor_penetration_pct", "ARMOR PEN", total_pen))
        phys_suppress = float(values.get("physical_suppression") or 0)
        if phys_suppress:
            items.append(cls._stat_item_pct("physical_suppression", "PHYS SUPPRESS", phys_suppress))

        return items

    @classmethod
    def _damage_breakdown_tooltip(
        cls,
        values: dict[str, float | int],
        prefix: str,
        *,
        base: float,
        spread: float,
    ) -> str | None:
        weapon_power = cls._optional_float(values.get(f"{prefix}_weapon_power"))
        stat_raw = cls._optional_float(values.get(f"{prefix}_stat_damage_raw"))
        stat_effective = cls._optional_float(values.get(f"{prefix}_stat_damage_effective"))
        mastery = cls._optional_float(values.get(f"{prefix}_mastery_factor"))
        raw_spread = cls._optional_float(values.get(f"{prefix}_damage_spread_raw"))

        if (
            weapon_power is None
            and stat_raw is None
            and stat_effective is None
            and mastery is None
            and raw_spread is None
        ):
            return None

        parts: list[str] = []
        if weapon_power is not None:
            parts.append(f"Оружие: {cls._round_display(weapon_power)}")
        if stat_raw is not None or stat_effective is not None:
            parts.append(f"Статы: {cls._round_display(stat_effective or 0.0)} из {cls._round_display(stat_raw or 0.0)}")
        if mastery is not None:
            parts.append(f"Владение: {cls._round_display(mastery * 100)}%")
        if raw_spread is not None:
            parts.append(f"Разброс: {cls._round_display(raw_spread * 100)}% -> {cls._round_display(spread * 100)}%")
        parts.append(f"База: {cls._round_display(base)}")
        return " // ".join(parts)

    @classmethod
    def _defense_items(cls, values: dict[str, float | int]) -> list[CombatStatValueDTO]:
        items: list[CombatStatValueDTO] = []

        armor = float(values.get("armor") or 0)
        if armor:
            items.append(cls._stat_item_raw("armor", "ARMOR", armor))

        phys_res = float(values.get("physical_resistance") or 0)
        if phys_res:
            items.append(cls._stat_item_pct("physical_resistance", "PHYS RESIST", phys_res))

        evasion = float(values.get("evasion") or 0)
        if evasion:
            items.append(cls._stat_item_pct("evasion", "EVASION", evasion))

        parry = float(values.get("parry") or 0)
        if parry:
            items.append(cls._stat_item_pct("parry", "PARRY", parry))

        block = float(values.get("block") or 0)
        if block:
            items.append(cls._stat_item_pct("block", "BLOCK", block))

        magic_resist = float(values.get("magic_resist") or 0)
        if magic_resist:
            items.append(cls._stat_item_pct("magic_resist", "MAGIC RESIST", magic_resist))

        return items

    @classmethod
    def _vitals_regen_items(cls, values: dict[str, float | int]) -> list[CombatStatValueDTO]:
        items: list[CombatStatValueDTO] = []
        for key, label in (("hp_regen", "HP REGEN"), ("en_regen", "EN REGEN"), ("stamina_regen", "CONC REGEN")):
            val = float(values.get(key) or 0)
            if val:
                items.append(CombatStatValueDTO(key=key, label=label, value=val, value_text=f"{val:.1f}"))
        initiative = values.get("initiative")
        if initiative:
            items.append(cls._stat_item_raw("initiative", "INITIATIVE", initiative))
        return items

    @classmethod
    def _status_resist_items(cls, values: dict[str, float | int]) -> list[CombatStatValueDTO]:
        return [
            cls._stat_item_pct(key, label, float(values[key])) for key, label in _STATUS_RESIST_ROWS if values.get(key)
        ]

    @classmethod
    def _caps_items(cls, values: dict[str, float | int]) -> list[CombatStatValueDTO]:
        return [cls._stat_item_pct(key, label, float(values[key])) for key, label in _CAP_ROWS if values.get(key)]

    @classmethod
    def _elemental_items(cls, values: dict[str, float | int]) -> list[CombatStatValueDTO]:
        items: list[CombatStatValueDTO] = []
        for elem in _ELEMENTAL_NAMES:
            name = elem.capitalize()
            dmg = float(values.get(f"{elem}_damage_bonus") or 0)
            res = float(values.get(f"{elem}_resistance") or 0)
            if dmg:
                items.append(cls._stat_item_pct(f"{elem}_damage_bonus", f"{name} DMG", dmg))
            if res:
                items.append(cls._stat_item_pct(f"{elem}_resistance", f"{name} RES", res))
        return items

    @staticmethod
    def _stat_item_pct(key: str, label: str, value: float) -> CombatStatValueDTO:
        pct = round(value * 100, 1)
        value_text = f"{int(pct)}%" if pct == int(pct) else f"{pct}%"
        return CombatStatValueDTO(key=key, label=label, value=value, value_text=value_text)

    @staticmethod
    def _stat_item_raw(key: str, label: str, value: float | int) -> CombatStatValueDTO:
        if isinstance(value, float):
            rounded = round(value, 1)
            value_text = str(int(rounded)) if rounded == int(rounded) else f"{rounded}"
        else:
            value_text = str(int(value)) if value == int(value) else str(value)
        return CombatStatValueDTO(key=key, label=label, value=value, value_text=value_text)

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
            params_raw = item.get("params")
            params = params_raw if isinstance(params_raw, dict) else {}
            result.append(
                CombatEffectBadgeDTO(
                    uid=CombatViewService._optional_str(item.get("uid")),
                    effect_id=str(item["effect_id"]),
                    expires_at_exchange=CombatViewService._optional_int(item.get("expire_at_exchange")),
                    impact=impact,
                    params=params,
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
        from src.backend.features.game_catalog.combat.resources.feints import get_feint_catalog_entry

        feints_raw = meta.get("feints")
        feints = feints_raw if isinstance(feints_raw, dict) else {}
        hand_raw = feints.get("hand")
        hand = hand_raw if isinstance(hand_raw, dict) else {}
        pinned = str(feints.get("pinned")) if feints.get("pinned") is not None else None
        options: list[CombatFeintOptionDTO] = []
        for feint_id, cost in hand.items():
            entry = get_feint_catalog_entry(str(feint_id))
            purchase_group = "basic"
            icon = ""
            if entry is not None:
                purchase_group = getattr(entry.technical, "purchase_group", "basic") or "basic"
                variant = entry.descriptive.variants.get(entry.descriptive.default_taxonomy)
                variant = variant or entry.descriptive.variants.get("humanoid")
                if variant is not None:
                    icon = variant.icon or ""
            options.append(
                CombatFeintOptionDTO(
                    feint_id=str(feint_id),
                    cost={str(k): CombatViewService._int(v) for k, v in cost.items()} if isinstance(cost, dict) else {},
                    pinned=str(feint_id) == pinned,
                    purchase_group=purchase_group,
                    icon=icon,
                )
            )
        return options

    @classmethod
    def _visible_tokens(cls, meta: dict[str, Any]) -> dict[str, int]:
        tokens_raw = meta.get("tokens")
        tokens_source = tokens_raw if isinstance(tokens_raw, dict) else {}
        return {str(k): cls._int(v) for k, v in tokens_source.items()}

    @classmethod
    def _visual_image_url(cls, visual: dict[str, Any]) -> str | None:
        for key in ("image_url", "generated_image_url", "fallback_image_url"):
            url = cls._avatar_image_url(visual.get(key), visual=visual)
            if key == "generated_image_url" and visual.get("status") != "generated":
                continue
            if url:
                return url
        return None

    @classmethod
    def _avatar_image_url(cls, value: object, *, visual: dict[str, Any] | None = None) -> str | None:
        url = cls._asset_url(value)
        if not url or "/static/images/monsters/families/" in url:
            return None
        return version_generated_asset_url(url, visual)

    @staticmethod
    def _asset_url(value: object) -> str | None:
        if value in (None, ""):
            return None
        url = str(value).strip()
        if not url or url.lower() in EMPTY_ASSET_URL_SENTINELS:
            return None
        return url

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
    def _optional_float(value: Any) -> float | None:
        if isinstance(value, bool) or value in (None, ""):
            return None
        with contextlib.suppress(TypeError, ValueError):
            return float(value)
        return None

    @staticmethod
    def _round_display(value: float) -> int:
        if value >= 0:
            return math.floor(value + 0.5)
        return math.ceil(value - 0.5)

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
