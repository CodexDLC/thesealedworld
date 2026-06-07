from __future__ import annotations

import copy
import json
import random
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from src.backend.features.combat.dto.session import SessionDataDTO
from src.backend.features.combat.game_config import CombatConfig
from src.backend.features.combat.runtime.engine.stats_engine import StatsEngine
from src.backend.features.combat.runtime.support.analytics_builder import CombatAnalyticsFactBuilder
from src.backend.infrastructure.actor_commitments import ActorCommitmentManager

if TYPE_CHECKING:
    from src.backend.features.combat.integrations import CombatSessionIntegration
    from src.backend.infrastructure.game_config.manager import GameConfigManager


class CombatLifecycleError(RuntimeError):
    """Raised when a combat session cannot be prepared."""


class CombatLifecycleService:
    """Creates RBC-compatible combat sessions from prepared actor snapshots."""

    SNAPSHOT_TIMEOUT_SECONDS = 10.0
    DEFAULT_TTL_SECONDS = int(CombatConfig.SESSION_TTL_SECONDS)

    def __init__(
        self,
        *,
        store: CombatSessionIntegration,
        game_config: GameConfigManager | None = None,
    ) -> None:
        self.store = store
        self.game_config = game_config

    async def create_session_from_snapshots(
        self,
        combat_id: str,
        *,
        battle_type: str,
        participants: dict[str, list[int | str]],
        snapshots: dict[str, dict[str, Any]],
        request: dict[str, Any],
    ) -> SessionDataDTO:
        ai_policy_id = await self._active_ai_policy_id()
        session_data = self._assemble_session_data(
            combat_id, battle_type, participants, snapshots, request, ai_policy_id=ai_policy_id
        )
        ttl = int(request.get("ttl") or await self._session_ttl_seconds())
        await self.store.create_session_batch(
            combat_id,
            session_data,
            ttl=ttl,
        )
        if hasattr(self.store, "append_analytics"):
            await self.store.append_analytics(
                combat_id,
                CombatAnalyticsFactBuilder.build_session_profile(combat_id=combat_id, session_data=session_data),
            )
        return session_data

    async def _session_ttl_seconds(self) -> int:
        if self.game_config is None:
            return self.DEFAULT_TTL_SECONDS
        return await self.game_config.get_int("combat", "SESSION_TTL_SECONDS", default=self.DEFAULT_TTL_SECONDS)

    async def _active_ai_policy_id(self) -> str:
        if self.game_config is None:
            return ""
        return await self.game_config.get_str("combat_ai", "ACTIVE_POLICY_ID", default="")

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
        *,
        ai_policy_id: str = "",
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
            "ai_policy_id": ai_policy_id,
            "arena_session_id": str(request.get("arena_session_id") or ""),
            "rift_session_id": str(request.get("rift_session_id") or ""),
            "rift_instance_id": str(request.get("rift_instance_id") or ""),
            "rift_node_id": str(request.get("rift_node_id") or ""),
            "rift_setting_key": str(request.get("rift_setting_key") or ""),
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
        skills = copy.deepcopy(combat.get("skills") or {})

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
        combatant_key = self._combatant_key(meta=meta, source=source, loadout=loadout, actor_type=actor_type)
        merged_raw = {
            "attributes": raw.get("attributes", {}),
            "modifiers": raw.get("modifiers", {}),
            "pipeline": raw.get("pipeline", {}),
            "rules": raw.get("rules", {}),
        }
        stats, explanation = StatsEngine.build_stats(raw=merged_raw, skills=skills, loadout=loadout)

        return {
            "meta": {
                "id": final_id,
                "name": name,
                "type": actor_type,
                "archetype": meta.get("archetype", "humanoid"),
                "ai_archetype": meta.get("ai_archetype", "balanced"),
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
                "combatant_key": combatant_key,
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
            "raw": merged_raw,
            "skills": skills,
            "loadout": loadout,
            "statuses": {"abilities": [], "effects": []},
            "xp_buffer": {},
            "metrics": {},
            "explanation": explanation,
            "stats": stats.model_dump(mode="json"),
            "source": source,
        }

    @staticmethod
    def _combatant_key(
        *,
        meta: dict[str, Any],
        source: dict[str, Any],
        loadout: dict[str, Any],
        actor_type: str,
    ) -> str:
        kind = CombatLifecycleService._combatant_kind(actor_type)
        explicit = (
            meta.get("combatant_key")
            or source.get("combatant_key")
            or meta.get("analytics_key")
            or source.get("analytics_key")
        )
        key = CombatLifecycleService._normalize_combatant_body(explicit)
        if not key:
            starting_imprint = (
                source.get("starting_imprint") if isinstance(source.get("starting_imprint"), dict) else {}
            )
            title = meta.get("imprint_title") or source.get("imprint_title") or starting_imprint.get("imprint_title")  # type: ignore
            key = CombatLifecycleService._key_from_title(title)
        if not key:
            key = CombatLifecycleService._key_from_loadout(loadout)
        if not key:
            return ""
        if str(key).startswith(f"{kind} "):
            return str(key)
        return f"{kind} {key}"

    @staticmethod
    def _combatant_kind(actor_type: Any) -> str:
        value = str(actor_type or "").strip().lower()
        if value == "monster":
            return "monster"
        if value == "shadow":
            return "shadow"
        return "player"

    @staticmethod
    def _normalize_combatant_body(value: Any) -> str:
        if isinstance(value, (list, tuple)):
            cleaned = "/".join(str(item).strip() for item in value if str(item).strip())
        elif isinstance(value, set):
            cleaned = "/".join(str(item).strip() for item in sorted(value) if str(item).strip())
        else:
            cleaned = str(value or "").strip()
        if not cleaned:
            return ""
        for prefix in ("player ", "monster ", "shadow "):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
        if cleaned.startswith("[") and cleaned.endswith("]"):
            return cleaned
        return f"[{cleaned}]"

    @staticmethod
    def _key_from_title(value: Any) -> str:
        raw = str(value or "")
        start = raw.rfind("[")
        end = raw.rfind("]")
        if start >= 0 and end > start:
            return raw[start : end + 1]
        return ""

    @staticmethod
    def _key_from_loadout(loadout: dict[str, Any]) -> str:
        layout = loadout.get("layout") if isinstance(loadout.get("layout"), dict) else {}
        equipment_refs = loadout.get("equipment_refs") if isinstance(loadout.get("equipment_refs"), dict) else {}
        surfaces = loadout.get("combat_surfaces") if isinstance(loadout.get("combat_surfaces"), dict) else {}
        codes: list[str] = []
        for slot in ("main_hand", "off_hand"):
            source = equipment_refs.get(slot) if isinstance(equipment_refs.get(slot), dict) else {}  # type: ignore
            surface = surfaces.get(slot) if isinstance(surfaces.get(slot), dict) else {}  # type: ignore
            skill_key = source.get("skill_key") or surface.get("skill_key") or layout.get(slot)  # type: ignore
            CombatLifecycleService._append_code(codes, CombatLifecycleService._SKILL_CODES.get(str(skill_key or "")))
        CombatLifecycleService._append_code(
            codes,
            CombatLifecycleService._SKILL_CODES.get(str(layout.get("tactical_style") or "")),  # type: ignore
        )
        armor_ref = equipment_refs.get("body") or equipment_refs.get("chest_armor") or {}  # type: ignore
        armor_skill = armor_ref.get("skill_key") if isinstance(armor_ref, dict) else None
        armor_class = armor_ref.get("armor_class") if isinstance(armor_ref, dict) else None
        CombatLifecycleService._append_code(
            codes,
            CombatLifecycleService._SKILL_CODES.get(str(armor_skill or ""))
            or CombatLifecycleService._ARMOR_CODES.get(str(armor_class or "")),
        )
        return f"[{'/'.join(codes)}]" if codes else ""

    @staticmethod
    def _append_code(values: list[str], code: str | None) -> None:
        if code and code not in values:
            values.append(code)

    _SKILL_CODES = {
        "skill_swords": "МЕ",
        "skill_macing": "БУ",
        "skill_fencing": "ФЕ",
        "skill_polearms": "ДК",
        "skill_archery": "ЛК",
        "skill_shield_mastery": "ЩТ",
        "skill_two_handed": "ДВ",
        "skill_dual_wield": "ДУ",
        "skill_ranged_combat": "ДБ",
        "skill_light_armor": "ЛБ",
        "skill_medium_armor": "СБ",
        "skill_heavy_armor": "ТБ",
    }
    _ARMOR_CODES = {
        "light": "ЛБ",
        "light_armor": "ЛБ",
        "medium": "СБ",
        "medium_armor": "СБ",
        "heavy": "ТБ",
        "heavy_armor": "ТБ",
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
