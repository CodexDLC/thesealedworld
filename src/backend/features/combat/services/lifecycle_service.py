from __future__ import annotations

import copy
import json
import random
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from src.backend.features.combat.dto.session import SessionDataDTO
from src.backend.features.combat.runtime.support.analytics_builder import CombatAnalyticsFactBuilder
from src.backend.infrastructure.actor_commitments import ActorCommitmentManager

if TYPE_CHECKING:
    from src.backend.features.combat.integrations import CombatSessionIntegration


class CombatLifecycleError(RuntimeError):
    """Raised when a combat session cannot be prepared."""


class CombatLifecycleService:
    """Creates RBC-compatible combat sessions from prepared actor snapshots."""

    SNAPSHOT_TIMEOUT_SECONDS = 10.0
    DEFAULT_TTL_SECONDS = 3600

    def __init__(
        self,
        *,
        store: CombatSessionIntegration,
    ) -> None:
        self.store = store

    async def create_session_from_snapshots(
        self,
        combat_id: str,
        *,
        battle_type: str,
        participants: dict[str, list[int | str]],
        snapshots: dict[str, dict[str, Any]],
        request: dict[str, Any],
    ) -> SessionDataDTO:
        session_data = self._assemble_session_data(combat_id, battle_type, participants, snapshots, request)
        await self.store.create_session_batch(
            combat_id,
            session_data,
            ttl=int(request.get("ttl") or self.DEFAULT_TTL_SECONDS),
        )
        if hasattr(self.store, "append_analytics"):
            await self.store.append_analytics(
                combat_id,
                CombatAnalyticsFactBuilder.build_session_profile(combat_id=combat_id, session_data=session_data),
            )
        return session_data

    async def complete_session(self, session_id: str, *, winner: str | None = None) -> None:
        if winner:
            await self.store.set_winner(session_id, winner)
        await self.store.cleanup_session(session_id)

    def _assemble_session_data(
        self,
        combat_id: str,
        battle_type: str,
        participants: dict[str, list[int | str]],
        snapshots: dict[str, dict[str, Any]],
        request: dict[str, Any],
    ) -> SessionDataDTO:
        actors: dict[str, dict[str, Any]] = {}
        teams: dict[str, list[str]] = {}
        actor_info: dict[str, str] = {}
        id_to_team: dict[str, str] = {}
        alive_counts: dict[str, int] = defaultdict(int)
        monster_instance_counts: dict[str, int] = defaultdict(int)

        for team_name, members in participants.items():
            teams[team_name] = []
            for raw_member in members:
                final_id, snapshot_id = self._resolve_member_identity(
                    combat_id,
                    raw_member,
                    monster_instance_counts,
                )
                snapshot = snapshots.get(snapshot_id)
                if not snapshot:
                    raise CombatLifecycleError(f"snapshot not found for participant {raw_member}")

                actors[final_id] = self._build_actor_doc(final_id, team_name, snapshot, battle_type=battle_type)
                teams[team_name].append(final_id)
                id_to_team[final_id] = team_name
                alive_counts[team_name] += 1
                actor_info[final_id] = "player" if self._is_player_actor_id(final_id) else "ai"

        now = int(time.time())
        meta = {
            "active": 1,
            "status": "active",
            "step_counter": 0,
            "start_time": now,
            "last_activity_at": now,
            "teams": json.dumps(teams),
            "actors_info": json.dumps(actor_info),
            "dead_actors": "[]",
            "alive_counts": json.dumps(alive_counts),
            "battle_type": battle_type,
            "location_id": str(request.get("location_id") or request.get("loc_id") or "arena"),
            "source": str(request.get("source") or "unknown"),
            "arena_session_id": str(request.get("arena_session_id") or ""),
            "rift_session_id": str(request.get("rift_session_id") or ""),
            "rift_instance_id": str(request.get("rift_instance_id") or ""),
            "rift_node_id": str(request.get("rift_node_id") or ""),
            "rift_event_scope": str(request.get("rift_event_scope") or ""),
            "rift_travel_id": str(request.get("rift_travel_id") or ""),
            "rift_event_key": str(request.get("rift_event_key") or ""),
            "rift_target_node_id": str(request.get("rift_target_node_id") or ""),
            "rift_entrance_seals_on_entry": bool(request.get("rift_entrance_seals_on_entry")),
        }
        return SessionDataDTO(meta=meta, actors=actors, targets=self._build_targets(id_to_team))

    def _build_actor_doc(
        self,
        final_id: str,
        team_name: str,
        snapshot: dict[str, Any],
        *,
        battle_type: str,
    ) -> dict[str, Any]:
        meta = snapshot.get("meta") or {}
        combat = snapshot.get("combat") or {}
        status = snapshot.get("status") or {}
        source = snapshot.get("source") or {}
        runtime = snapshot.get("runtime") or {}
        loadout = copy.deepcopy(combat.get("loadout") or {})
        raw = copy.deepcopy(combat.get("math_model") or {})

        name = meta.get("name") or source.get("name") or f"Actor {final_id}"
        avatar_url = meta.get("avatar_url") or source.get("avatar_url")
        is_shadow = battle_type == "shadow" and final_id.startswith("-")
        actor_type = str(meta.get("actor_type") or "player")
        if is_shadow:
            name = f"Shadow {name}"
            actor_type = "shadow"
        tags = self._actor_tags(meta, source, is_shadow=is_shadow)
        visual = source.get("visual") if isinstance(source.get("visual"), dict) else {}

        hp = self._vital(status, runtime, "hp", "hp_current", default=100)
        max_hp = max(hp, self._vital_max(status, runtime, "hp", ("max_hp", "hp_max"), default=hp))
        energy = self._vital(status, runtime, "energy", "energy_current", default=100)
        max_energy = max(
            energy,
            self._vital_max(
                status,
                runtime,
                "energy",
                ("max_energy", "energy_max", "max_en", "en_max"),
                default=energy,
            ),
        )
        stamina = self._vital(status, runtime, "stamina", "stamina_current", default=100)
        max_stamina = max(
            stamina,
            self._vital_max(
                status,
                runtime,
                "stamina",
                ("max_stamina", "stamina_max"),
                default=stamina,
            ),
        )
        known_feints = loadout.get("known_feints") or loadout.get("feints") or []

        return {
            "meta": {
                "id": final_id,
                "name": name,
                "type": actor_type,
                "archetype": meta.get("archetype", "humanoid"),
                "avatar_url": avatar_url,
                "gender": meta.get("gender") or source.get("gender"),
                "role": meta.get("role") or source.get("role"),
                "tags": tags,
                "source_ref": self._source_ref(actor_type, source, final_id),
                "visual": visual,
                "team": team_name,
                "template_id": str(
                    source.get("character_id")
                    or source.get("monster_id")
                    or source.get("template_id")
                    or meta.get("actor_id")
                    or final_id
                ),
                "is_ai": not self._is_player_actor_id(final_id),
                "hp": hp,
                "max_hp": max_hp,
                "en": energy,
                "max_en": max_energy,
                "stamina": stamina,
                "max_stamina": max_stamina,
                "tactics": 0,
                "is_dead": False,
                "afk_level": 0,
                "exchange_counter": 0,
                "tokens": {},
                "token_progress": {},
                "feints": {"arsenal": known_feints, "hand": {}, "pinned": None},
            },
            "raw": {
                "attributes": raw.get("attributes", {}),
                "modifiers": raw.get("modifiers", {}),
                "pipeline": raw.get("pipeline", {}),
                "rules": raw.get("rules", {}),
            },
            "skills": copy.deepcopy(combat.get("skills") or {}),
            "loadout": loadout,
            "statuses": {"abilities": [], "effects": []},
            "xp_buffer": {},
            "metrics": {},
            "explanation": {},
            "source": source,
        }

    @staticmethod
    def _actor_tags(meta: dict[str, Any], source: dict[str, Any], *, is_shadow: bool) -> list[str]:
        tags: list[str] = []
        for raw in (meta.get("tags"), source.get("tags")):
            if isinstance(raw, list):
                tags.extend(str(tag) for tag in raw if tag)
        if is_shadow:
            tags.append("shadow")
        return sorted(set(tags))

    @staticmethod
    def _source_ref(actor_type: str, source: dict[str, Any], final_id: str) -> str:
        monster_id = source.get("monster_id")
        if monster_id:
            return ActorCommitmentManager.source_ref("monster", str(monster_id))
        character_id = source.get("character_id")
        if character_id:
            return ActorCommitmentManager.source_ref("player", str(character_id))
        if actor_type == "monster":
            return ActorCommitmentManager.source_ref("monster", final_id)
        return ActorCommitmentManager.source_ref("player", final_id.lstrip("-"))

    @staticmethod
    def prepare_participants(request: dict[str, Any], *, battle_type: str) -> dict[str, list[int | str]]:
        raw = request.get("participants") or {}
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, dict):
            raise CombatLifecycleError("participants must be a team mapping")
        return {str(team): list(members or []) for team, members in raw.items()}

    @staticmethod
    def is_shadow_participants(request: dict[str, Any], participants: dict[str, list[int | str]]) -> bool:
        if request.get("battle_type") == "shadow":
            return True
        return len([member for members in participants.values() for member in members]) == 1

    @staticmethod
    def shadow_participants(
        request: dict[str, Any],
        participants: dict[str, list[int | str]],
    ) -> dict[str, list[int | str]]:
        requested_by = request.get("requested_by")
        if requested_by is None:
            for members in participants.values():
                if members:
                    requested_by = members[0]
                    break
        if requested_by is None:
            raise CombatLifecycleError("shadow combat requires requested_by")
        char_id = int(requested_by)
        return {"team_1": [char_id], "team_2": [f"-{char_id}"]}

    @staticmethod
    def player_snapshot_ids(participants: dict[str, list[int | str]]) -> list[int]:
        ids: list[int] = []
        for members in participants.values():
            for member in members:
                value = str(member)
                if value.isdigit():
                    ids.append(int(value))
                elif value.startswith("-") and value[1:].isdigit():
                    ids.append(int(value[1:]))
        return list(dict.fromkeys(ids))

    @staticmethod
    def monster_snapshot_ids(participants: dict[str, list[int | str]]) -> list[str]:
        ids: list[str] = []
        for members in participants.values():
            for member in members:
                value = str(member)
                if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
                    continue
                ids.append(value)
        return list(dict.fromkeys(ids))

    @staticmethod
    def _resolve_member_identity(
        combat_id: str,
        raw_member: int | str,
        monster_instance_counts: dict[str, int],
    ) -> tuple[str, str]:
        value = str(raw_member)
        if value.isdigit():
            return value, ActorCommitmentManager.source_ref("player", value)
        if value.startswith("-") and value[1:].isdigit():
            return value, ActorCommitmentManager.source_ref("player", value[1:])

        monster_instance_counts[value] += 1
        return f"{value}_{monster_instance_counts[value]}", ActorCommitmentManager.source_ref("monster", value)

    @staticmethod
    def _is_player_actor_id(actor_id: str) -> bool:
        return actor_id.isdigit()

    @staticmethod
    def _build_targets(id_to_team: dict[str, str]) -> dict[str, list[str]]:
        targets: dict[str, list[str]] = {}
        for actor_id, team_name in id_to_team.items():
            enemies = [other_id for other_id, other_team in id_to_team.items() if other_team != team_name]
            random.shuffle(enemies)
            targets[actor_id] = enemies
        return targets

    @staticmethod
    def _vital(status: dict[str, Any], runtime: dict[str, Any], key: str, legacy_key: str, *, default: int) -> int:
        value = status.get(legacy_key)
        status_v = status.get(key)
        if value is None and isinstance(status_v, dict):
            value = status_v.get("cur")

        vitals_raw = runtime.get("vitals")
        runtime_vitals = vitals_raw if isinstance(vitals_raw, dict) else {}

        if value is None:
            value = runtime_vitals.get(legacy_key)

        runtime_v = runtime_vitals.get(key)
        if value is None and isinstance(runtime_v, dict):
            value = runtime_v.get("cur")

        if value is None or value == -1:
            value = default
        try:
            return max(1, int(value))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _vital_max(
        status: dict[str, Any],
        runtime: dict[str, Any],
        key: str,
        legacy_keys: tuple[str, ...],
        *,
        default: int,
    ) -> int:
        value = next(
            (status.get(legacy_key) for legacy_key in legacy_keys if status.get(legacy_key) is not None),
            None,
        )
        status_v = status.get(key)
        if value is None and isinstance(status_v, dict):
            value = status_v.get("max")

        vitals_raw = runtime.get("vitals")
        runtime_vitals = vitals_raw if isinstance(vitals_raw, dict) else {}

        if value is None:
            value = next(
                (
                    runtime_vitals.get(legacy_key)
                    for legacy_key in legacy_keys
                    if runtime_vitals.get(legacy_key) is not None
                ),
                None,
            )

        runtime_v = runtime_vitals.get(key)
        if value is None and isinstance(runtime_v, dict):
            value = runtime_v.get("max")

        if value is None or value == -1:
            value = default
        try:
            return max(1, int(value))
        except (ValueError, TypeError):
            return default
