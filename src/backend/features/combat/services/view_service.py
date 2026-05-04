from __future__ import annotations

import contextlib
import json
from typing import Any, Literal

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
    ) -> CombatDashboardDTO:
        hero_raw = actors.get(str(viewer_id))
        if not hero_raw:
            raise ValueError(f"Actor {viewer_id} is not present in combat session {session_id}")

        hero = self._map_actor(str(viewer_id), hero_raw, is_target=False)
        target = self._resolve_target(str(viewer_id), targets, actors)
        target_id = target.actor_id if target else None
        allies: list[CombatActorCardDTO] = []
        enemies: list[CombatActorCardDTO] = []

        for actor_id, actor_raw in actors.items():
            if actor_id == str(viewer_id) or not actor_raw:
                continue
            card = self._map_actor(actor_id, actor_raw, is_target=actor_id == target_id)
            if card.team == hero.team:
                allies.append(card)
            else:
                enemies.append(card)

        allies.sort(key=lambda actor: (actor.is_dead, actor.name))
        enemies.sort(key=lambda actor: (actor.is_dead, actor.name))
        status = self._status(meta, hero, target)

        return CombatDashboardDTO(
            session_id=session_id,
            turn_number=self._int(meta.get("step_counter")),
            status=status,
            hero=hero,
            target=target,
            allies=allies,
            enemies=enemies,
            active_effects=hero.active_effects,
            feints=hero.feints,
            available_actions=self._available_actions(status, target, hero),
            events_delta=CombatDeltaDTO(events=self.parse_logs(raw_logs)),
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
                events.append(
                    CombatEventDTO(
                        type=str(parsed.get("type") or "log"),
                        text=cls._optional_str(parsed.get("text")),
                        timestamp=parsed.get("timestamp") if isinstance(parsed.get("timestamp"), int | float) else None,
                        tags=[str(tag) for tag in parsed.get("tags", []) if tag],
                        data={k: v for k, v in parsed.items() if k not in {"type", "text", "timestamp", "tags"}},
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
    ) -> CombatActorCardDTO | None:
        queue = targets.get(viewer_id)
        if not queue:
            return None
        target_id = str(queue[0])
        target_raw = actors.get(target_id)
        if not target_raw:
            return None
        return self._map_actor(target_id, target_raw, is_target=True)

    def _map_actor(self, actor_id: str, actor: dict[str, Any], *, is_target: bool) -> CombatActorCardDTO:
        meta_raw = actor.get("meta")
        meta = meta_raw if isinstance(meta_raw, dict) else {}
        
        loadout_raw = actor.get("loadout")
        loadout = loadout_raw if isinstance(loadout_raw, dict) else {}
        
        statuses_raw = actor.get("statuses")
        statuses = statuses_raw if isinstance(statuses_raw, dict) else {}

        tokens_raw = meta.get("tokens")
        tokens = tokens_raw if isinstance(tokens_raw, dict) else {}

        return CombatActorCardDTO(
            actor_id=str(meta.get("id") or actor_id),
            name=str(meta.get("name") or actor_id),
            actor_type=str(meta.get("type") or "unknown"),
            team=str(meta.get("team") or "neutral"),
            avatar_url=self._optional_str(meta.get("avatar_url")),
            is_ai=bool(meta.get("is_ai", False)),
            is_dead=bool(meta.get("is_dead", False)) or self._int(meta.get("hp")) <= 0,
            is_target=is_target,
            vitals=CombatActorVitalsDTO(
                hp_current=self._int(meta.get("hp")),
                hp_max=self._int(meta.get("max_hp")),
                energy_current=self._int(meta.get("en")),
                energy_max=self._int(meta.get("max_en")),
                tactics=self._int(meta.get("tactics")),
            ),
            weapon_type=self._weapon_type(loadout),
            tokens={str(k): self._int(v) for k, v in tokens.items()},
            active_effects=self._effects(statuses),
            active_abilities=self._abilities(statuses),
            feints=self._feints(meta),
        )

    def _available_actions(
        self,
        status: str,
        target: CombatActorCardDTO | None,
        hero: CombatActorCardDTO,
    ) -> list[CombatActionOptionDTO]:
        actions = [
            CombatActionOptionDTO(action="system", label="Обновить", enabled=True),
            CombatActionOptionDTO(action="system", label="Сбежать", enabled=not hero.is_dead),
        ]
        if status == "active" and target is not None and not hero.is_dead:
            actions.insert(
                0,
                CombatActionOptionDTO(action="exchange", label="Атака", target_id=target.actor_id, catalog_ref="triggers"),
            )
            actions.extend(
                CombatActionOptionDTO(
                    action="instant",
                    label=feint.feint_id,
                    target_id=target.actor_id,
                    feint_id=feint.feint_id,
                    catalog_ref="feints",
                )
                for feint in hero.feints
            )
        return actions

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
    def _weapon_type(loadout: dict[str, Any]) -> str | None:
        layout_raw = loadout.get("layout") or loadout.get("equipment_layout")
        layout = layout_raw if isinstance(layout_raw, dict) else {}
        return CombatViewService._optional_str(
            layout.get("main_hand") or layout.get("weapon") or layout.get("slot_weapon")
        )

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
                    expires_at_exchange=CombatViewService._optional_int(
                        item.get("expire_at_exchange")
                    ),
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
                    expires_at_exchange=CombatViewService._optional_int(
                        item.get("expire_at_exchange")
                    ),
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
                cost={str(k): CombatViewService._int(v) for k, v in cost.items()}
                if isinstance(cost, dict)
                else {},
            )
            for feint_id, cost in hand.items()
        ]

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
