from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.features.monsters.intel_projector import MonsterIntelProjector
from src.backend.features.rift.dto.screen import RiftCombatPromptDTO, RiftCombatPromptEnemyDTO
from src.backend.features.rift.runtime.encounter import composition_policy_for_encounter_kind

if TYPE_CHECKING:
    from src.backend.features.combat.orchestrators import CombatCreationOrchestrator
    from src.backend.features.monsters.dto import MonsterGroupResult
    from src.backend.features.monsters.services import MonsterGroupService
    from src.backend.features.rift.dto import RiftZoneRuntimeDTO
    from src.backend.features.rift.integrations import RiftRuntimeIntegration
    from src.backend.infrastructure.actor_state.managers import CharacterSessionManager


class RiftEncounterService:
    """Prepares rift monster groups and can launch the real combat runtime."""

    def __init__(
        self,
        *,
        monster_groups: MonsterGroupService,  # type: ignore
        combat_creator: CombatCreationOrchestrator | None = None,
        runtime: RiftRuntimeIntegration | None = None,
        character_sessions: CharacterSessionManager | None = None,
    ) -> None:
        self.monster_groups = monster_groups
        self.combat_creator = combat_creator
        self.runtime = runtime
        self.character_sessions = character_sessions

    async def enrich_combat_prompt(
        self,
        runtime: RiftZoneRuntimeDTO,
        *,
        session: dict[str, Any],
        prompt: RiftCombatPromptDTO,
    ) -> RiftCombatPromptDTO:
        metadata = dict(prompt.metadata or {})
        encounter_kind = str(metadata.get("encounter_kind") or metadata.get("event_scope") or "transition")
        group = await self.prepare_group(runtime, session=session, encounter_kind=encounter_kind, metadata=metadata)
        request = self._combat_request(runtime, session=session, group=group, metadata=metadata)
        intel = MonsterIntelProjector().project_group(group, hunting_skill=await self._hunting_skill(session))
        description = _select_clan_encounter_text(group.encounter_texts, metadata=metadata)
        return prompt.model_copy(
            update={
                "description": description,
                "enemies": [
                    RiftCombatPromptEnemyDTO.model_validate(
                        {
                            **enemy.model_dump(mode="json"),
                            "tier": enemy.member_tier,
                        }
                    )
                    for enemy in intel.enemies
                ],
                "metadata": {
                    **metadata,
                    "monster_intel": intel.model_dump(mode="json"),
                    "monster_group": group.model_dump(mode="json"),
                    "combat": {
                        "status": "ready",
                        "battle_type": "rift",
                        "request": request,
                    },
                },
            }
        )

    async def _hunting_skill(self, session: dict[str, Any]) -> float:
        entry_context = dict(session.get("entry_context") or {})
        skills = dict(entry_context.get("skills") or {})
        if "skill_hunting" in skills:
            return _normalized_skill(skills.get("skill_hunting"))
        char_id = _optional_participant_char_id(session)
        getter = getattr(self.character_sessions, "get_skills", None)
        if char_id is not None and getter is not None:
            raw_skills = await getter(char_id)
            if isinstance(raw_skills, dict):
                return _normalized_skill(raw_skills.get("skill_hunting"))
        return 0.0

    async def launch_combat_from_prompt(
        self,
        runtime: RiftZoneRuntimeDTO,
        *,
        session: dict[str, Any],
        prompt: RiftCombatPromptDTO,
    ) -> RiftCombatPromptDTO:
        if self.combat_creator is None or self.runtime is None or self.character_sessions is None:
            return await self.enrich_combat_prompt(runtime, session=session, prompt=prompt)

        existing_combat_id = str(session.get("active_encounter_id") or "")
        if existing_combat_id:
            if await self._active_encounter_belongs_to_character(session, existing_combat_id):
                return self._mark_prompt_started(prompt, combat_id=existing_combat_id)
            await self._resolve_stale_active_encounter(session, prompt=prompt, combat_id=existing_combat_id)

        enriched = await self.enrich_combat_prompt(runtime, session=session, prompt=prompt)
        combat_meta = dict(enriched.metadata.get("combat") or {})
        request = dict(combat_meta.get("request") or {})
        if not request:
            raise ValueError("Rift combat prompt does not contain combat request")

        ready = await self.combat_creator.create_from_request(request)
        combat_id = str(ready.get("combat_id") or request.get("combat_id") or "")
        if not combat_id:
            raise ValueError("Combat service did not return combat_id")

        rift_session_id = str(session.get("rift_session_id") or "")
        participant_ref = str(session.get("participant_ref") or f"char:{request['requested_by']}")
        await self.runtime.set_run_active_encounter(rift_session_id, combat_id)
        await self.runtime.join_transition_encounter(runtime.rift_instance_id, combat_id, participant_ref)
        await self.character_sessions.set_combat_session(int(request["requested_by"]), combat_id)
        return self._mark_prompt_started(enriched, combat_id=combat_id)

    async def prepare_group(
        self,
        runtime: RiftZoneRuntimeDTO,
        *,
        session: dict[str, Any],
        encounter_kind: str,
        metadata: dict[str, Any] | None = None,
    ) -> MonsterGroupResult:
        metadata = dict(metadata or {})
        node_id = _encounter_node_id(runtime, session=session, metadata=metadata)

        population = dict(runtime.population_context or {})
        budget = _combat_budget(session)
        setting_key = str(population.get("setting_key") or dict(runtime.setting or {}).get("setting_key") or "")
        if not setting_key:
            raise ValueError("Rift encounter requires setting_key for habitat clan pool lookup")
        return await self.monster_groups.prepare_monster_group_for_scope(  # type: ignore
            scope_type="rift",
            scope_id=setting_key,
            budget=budget,
            tier=max(1, int(population.get("tier") or dict(runtime.setting or {}).get("tier") or 1)),
            danger=float(population.get("danger") or 0.0),
            biome_id=str(population.get("biome_id") or "rift"),
            loc_id=f"rift:{runtime.rift_instance_id}:{node_id}",
            zone_id=f"rift:{runtime.rift_instance_id}:{runtime.current_zone_key}",
            composition_policy=composition_policy_for_encounter_kind(encounter_kind),
            group_scope_id=f"rift:{session.get('rift_session_id') or runtime.rift_instance_id}:{node_id}:{encounter_kind}",
            ttl=900,
        )

    def _combat_request(
        self,
        runtime: RiftZoneRuntimeDTO,
        *,
        session: dict[str, Any],
        group: MonsterGroupResult,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        char_id = _participant_char_id(session)
        monster_ids = list(group.monster_ids)
        policy = dict(session.get("exit_policy") or {})
        node_id = _encounter_node_id(runtime, session=session, metadata=metadata)
        setting_key = str(dict(runtime.setting or {}).get("setting_key") or "")
        return {
            "combat_id": _combat_id(runtime, session=session, metadata=metadata),
            "source": "rift",
            "battle_type": "rift",
            "requested_by": char_id,
            "rift_session_id": str(session.get("rift_session_id") or ""),
            "rift_instance_id": runtime.rift_instance_id,
            "rift_node_id": node_id,
            "rift_setting_key": setting_key,
            "rift_event_scope": str(metadata.get("event_scope") or ""),
            "rift_travel_id": str(metadata.get("travel_id") or ""),
            "rift_event_key": str(metadata.get("event_key") or ""),
            "rift_target_node_id": str(metadata.get("to_node_id") or node_id),
            "rift_entrance_seals_on_entry": bool(policy.get("entrance_seals_on_entry", True)),
            "participants": {"team_1": [char_id], "team_2": monster_ids},
            "commitments": dict(group.actor_commitments),
            "location_id": f"rift:{runtime.rift_instance_id}:{node_id}",
            "metadata": {
                "monster_group_id": group.group_id,
                "monster_group_key": group.group_key,
                "clan_id": group.clan_id,
                "family_id": group.family_id,
            },
        }

    @staticmethod
    def _mark_prompt_started(prompt: RiftCombatPromptDTO, *, combat_id: str) -> RiftCombatPromptDTO:
        metadata = dict(prompt.metadata or {})
        combat = dict(metadata.get("combat") or {})
        metadata["combat"] = {
            **combat,
            "status": "started",
            "battle_type": combat.get("battle_type") or "rift",
            "combat_id": combat_id,
        }
        return prompt.model_copy(update={"metadata": metadata})

    async def _active_encounter_belongs_to_character(self, session: dict[str, Any], combat_id: str) -> bool:
        char_id = _optional_participant_char_id(session)
        getter = getattr(self.character_sessions, "get_session", None)
        if char_id is None or getter is None:
            return True
        character_session = await getter(char_id)
        if not isinstance(character_session, dict):
            return True
        raw_sessions = character_session.get("sessions")
        sessions = raw_sessions if isinstance(raw_sessions, dict) else {}
        return str(sessions.get("combat_id") or "") == str(combat_id)

    async def _resolve_stale_active_encounter(
        self,
        session: dict[str, Any],
        *,
        prompt: RiftCombatPromptDTO,
        combat_id: str,
    ) -> None:
        """Unstick a rift session whose active_encounter no longer matches the player's combat_id.

        Clears the encounter binding without applying any combat result — the previous
        encounter is treated as abandoned, not auto-victory. Failures in clearing are
        logged and swallowed so the new combat can still be launched.
        """
        rift_session_id = str(session.get("rift_session_id") or "")
        rift_instance_id = str(session.get("rift_instance_id") or "")
        clear_run_active_encounter = getattr(self.runtime, "clear_run_active_encounter", None)
        clear_encounter_presence = getattr(self.runtime, "clear_transition_encounter_presence", None)
        try:
            if clear_run_active_encounter is not None and rift_session_id:
                await clear_run_active_encounter(rift_session_id)
            if clear_encounter_presence is not None and rift_instance_id and combat_id:
                await clear_encounter_presence(rift_instance_id, combat_id)
        except Exception:  # noqa: BLE001
            logger.bind(
                rift_session_id=rift_session_id,
                rift_instance_id=rift_instance_id,
                stale_combat_id=combat_id,
            ).warning("RiftStaleEncounterForceClearFailed")
        else:
            logger.bind(
                rift_session_id=rift_session_id,
                rift_instance_id=rift_instance_id,
                stale_combat_id=combat_id,
            ).info("RiftStaleEncounterForceCleared")
        # Drop unused arg now that we no longer dispatch into apply_combat_result.
        _ = prompt


def _combat_budget(session: dict[str, Any]) -> float:
    entry_context = dict(session.get("entry_context") or {})
    combat_power = dict(entry_context.get("combat_power") or {})
    value = combat_power.get("player_gear_score") or combat_power.get("party_gear_score") or 1
    try:
        return max(1.0, float(value))
    except (TypeError, ValueError):
        return 1.0


def _optional_participant_char_id(session: dict[str, Any]) -> int | None:
    try:
        return _participant_char_id(session)
    except ValueError:
        return None


def _participant_char_id(session: dict[str, Any]) -> int:
    for key in ("participant_ref", "owner_id"):
        value = str(session.get(key) or "")
        if value.startswith("char:"):
            value = value.removeprefix("char:")
        if value.isdigit():
            return int(value)
    raise ValueError("Rift combat request requires character participant_ref")


def _normalized_skill(value: Any) -> float:
    try:
        raw = max(0.0, float(value or 0.0))
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, raw / 100.0 if raw > 1.0 else raw)


def _select_clan_encounter_text(
    encounter_texts: dict[str, Any],
    *,
    metadata: dict[str, Any],
) -> str:
    key = _encounter_text_key(metadata)
    value = encounter_texts.get(key)
    if not value:
        raise ValueError(f"Missing clan encounter text for key={key}")
    return str(value)


def _encounter_text_key(metadata: dict[str, Any]) -> str:
    encounter_kind = str(metadata.get("encounter_kind") or "").strip()
    event_scope = str(metadata.get("event_scope") or "").strip()
    if encounter_kind in {"ambush", "surprise", "ambush_detected"}:
        return "ambush"
    if encounter_kind in {"heart_guard", "key_guard", "guard", "boss", "boss_solo", "boss_with_minions"}:
        return "lair"
    if encounter_kind in {"ordinary", "ordinary_node"}:
        return "random_meeting" if event_scope == "node_entry" else "patrol"
    if event_scope == "node_entry":
        return "lair"
    return "patrol"


def _combat_id(runtime: RiftZoneRuntimeDTO, *, session: dict[str, Any], metadata: dict[str, Any]) -> str:
    raw = ":".join(
        [
            str(session.get("rift_session_id") or runtime.rift_instance_id),
            str(metadata.get("event_scope") or "encounter"),
            str(metadata.get("travel_id") or metadata.get("event_key") or ""),
            str(metadata.get("to_node_id") or session.get("current_node_id") or runtime.current_node_id),
        ]
    )
    digest = hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()[:20]
    return f"rift-{digest}"


def _encounter_node_id(
    runtime: RiftZoneRuntimeDTO,
    *,
    session: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    return str(metadata.get("to_node_id") or session.get("current_node_id") or runtime.current_node_id)
