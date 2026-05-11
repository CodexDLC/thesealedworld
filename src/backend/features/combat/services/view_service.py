from __future__ import annotations

import contextlib
import json
import re
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

        log_turns = self.parse_logs_by_turn(raw_logs_by_turn) if raw_logs_by_turn is not None else []
        log_events = self._flatten_turn_events(log_turns) if log_turns else self.parse_logs(raw_logs)

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
            events_delta=CombatDeltaDTO(events=log_events, turns=log_turns),
            log_total=total_logs if total_logs is not None else len(raw_logs),
            winner_team=self._optional_str(meta.get("winner")),
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
