"""Build simulation actors from real character starting imprints."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from src.backend.features.character.resources.starting_imprints import STARTING_IMPRINTS
from src.backend.features.character.runtime import CharacterCombatActorInputBuilder
from src.backend.features.character.runtime.gear_score import CharacterGearScoreCalculator
from src.backend.features.character.services.starting_imprint_service import (
    StartingImprintBuild,
    StartingImprintService,
)
from src.backend.features.combat.dto import ActorLoadoutDTO, ActorMetaDTO, ActorRawDTO, ActorSnapshot, FeintHandDTO
from src.backend.features.combat.runtime.engine.feint_service import FeintService
from src.backend.features.combat.runtime.engine.stats_engine import StatsEngine
from src.backend.features.items.dto.instance import ItemGenerationRequestDTO, ItemOriginRefDTO
from src.backend.features.items.runtime.item_factory import ItemFactory

DEFAULT_STARTER_SIMULATION_IMPRINTS: tuple[str, ...] = (
    "starter_guard_01",
    "starter_tactician_01",
    "starter_heavy_guard_01",
    "starter_breaker_01",
    "starter_hunter_01",
    "starter_rift_survivor_01",
    "starter_archer_01",
    "starter_dual_blades_01",
    "starter_dual_sword_01",
    "starter_dual_mace_01",
)
STARTER_SKILL_PROFILE_BASELINE = "baseline"
STARTER_SKILL_PROFILE_MAXED_EXISTING = "maxed_existing_skills"
STARTER_SIMULATION_BEHAVIOR_PROFILES: tuple[str, ...] = ("aggressive",)

STARTER_5V5_BLUE = DEFAULT_STARTER_SIMULATION_IMPRINTS[:5]
STARTER_5V5_RED = DEFAULT_STARTER_SIMULATION_IMPRINTS[5:10]

STARTER_SIMULATION_NAMES: dict[str, str] = {
    "starter_guard_01": "Ada Guard",
    "starter_breaker_01": "Borin Breaker",
    "starter_dual_blades_01": "Dax Twinblades",
    "starter_dual_sword_01": "Mara Bladehand",
    "starter_dual_mace_01": "Nox Ironhand",
    "starter_hunter_01": "Fenn Hunter",
    "starter_archer_01": "Galen Archer",
    "starter_heavy_guard_01": "Ivar Bulwark",
    "starter_tactician_01": "Juno Tactician",
    "starter_rift_survivor_01": "Kael Survivor",
}

STARTER_SIMULATION_ARCHETYPES: dict[str, str] = {
    "starter_guard_01": "bulwark",
    "starter_breaker_01": "berserker",
    "starter_dual_blades_01": "duelist",
    "starter_dual_sword_01": "duelist",
    "starter_dual_mace_01": "bulwark",
    "starter_hunter_01": "duelist",
    "starter_archer_01": "duelist",
    "starter_heavy_guard_01": "bulwark",
    "starter_tactician_01": "tactician",
    "starter_rift_survivor_01": "balanced",
}


@dataclass(frozen=True, slots=True)
class StartingImprintSimulationActor:
    actor: ActorSnapshot
    participant: dict[str, Any]


class StartingImprintSimulationActorBuilder:
    """Materialise real starter builds into combat ActorSnapshot objects."""

    def __init__(
        self,
        *,
        imprints: StartingImprintService | None = None,
        items: ItemFactory | None = None,
        combat_input: CharacterCombatActorInputBuilder | None = None,
    ) -> None:
        self.imprints = imprints or StartingImprintService()
        self.items = items or ItemFactory()
        self.combat_input = combat_input or CharacterCombatActorInputBuilder()

    def build_actor(
        self,
        imprint_key: str,
        *,
        actor_id: str,
        team: str,
        name: str | None = None,
        ai_archetype: str | None = None,
        ai_behavior_profile: str | None = None,
        skill_profile: str = STARTER_SKILL_PROFILE_BASELINE,
    ) -> StartingImprintSimulationActor:
        build = self.imprints.build(imprint_key)
        actor_name = name or STARTER_SIMULATION_NAMES.get(imprint_key) or build.title
        active_character = self._active_character(
            build,
            actor_id=actor_id,
            name=actor_name,
            team=team,
            skill_profile=skill_profile,
        )
        actor_input = self.combat_input.build_input(active_character)
        loadout = dict(actor_input["loadout"])
        known_feints = [str(feint_id) for feint_id in loadout.get("known_feints") or []]
        snapshot = ActorSnapshot(
            meta=ActorMetaDTO(
                id=actor_id,
                name=actor_name,
                type="player-model",
                team=team,
                template_id=build.imprint_key,
                is_ai=True,
                archetype="humanoid",
                ai_archetype=ai_archetype or STARTER_SIMULATION_ARCHETYPES.get(imprint_key, "balanced"),
                ai_behavior_profile=ai_behavior_profile
                or _starter_behavior_profile(
                    imprint_key=imprint_key,
                    actor_id=actor_id,
                ),
                hp=1,
                max_hp=1,
                en=1,
                max_en=1,
                stamina=1,
                max_stamina=1,
                tokens={"hit": 4, "crit": 4, "block": 4, "parry": 4, "dodge": 4, "tempo": 4, "blood": 2, "gift": 2},
                feints=FeintHandDTO(arsenal=known_feints, hand={}),
            ),
            raw=ActorRawDTO.model_validate(actor_input["raw"]),
            skills=dict(actor_input["skills"]),
            loadout=ActorLoadoutDTO.model_validate(loadout),
        )
        StatsEngine.ensure_stats(snapshot)
        self._hydrate_resources(snapshot)
        FeintService.refill_hand(snapshot.meta, hand_size=3)
        participant = self._participant(snapshot, build, known_feints, skill_profile=skill_profile)
        return StartingImprintSimulationActor(actor=snapshot, participant=participant)

    def build_roster(
        self,
        *,
        blue_imprints: tuple[str, ...] = STARTER_5V5_BLUE,
        red_imprints: tuple[str, ...] = STARTER_5V5_RED,
        seed: int | None = None,
        behavior_seed: int | None = None,
        min_team_size: int = 5,
        max_team_size: int = 5,
        skill_profile: str = STARTER_SKILL_PROFILE_BASELINE,
    ) -> tuple[list[ActorSnapshot], list[dict[str, Any]]]:
        if seed is not None:
            blue_imprints, red_imprints = random_starter_roster_imprints(
                seed=seed,
                min_team_size=min_team_size,
                max_team_size=max_team_size,
            )
        actors: list[ActorSnapshot] = []
        participants: list[dict[str, Any]] = []
        for index, imprint_key in enumerate(blue_imprints, start=1):
            built = self.build_actor(
                imprint_key,
                actor_id=f"blue_{index}_{imprint_key}",
                team="blue",
                ai_behavior_profile=_starter_behavior_profile(
                    imprint_key=imprint_key,
                    actor_id=f"blue_{index}_{imprint_key}",
                    seed=behavior_seed if behavior_seed is not None else seed,
                ),
                skill_profile=skill_profile,
            )
            actors.append(built.actor)
            participants.append(built.participant)
        for index, imprint_key in enumerate(red_imprints, start=1):
            built = self.build_actor(
                imprint_key,
                actor_id=f"red_{index}_{imprint_key}",
                team="red",
                ai_behavior_profile=_starter_behavior_profile(
                    imprint_key=imprint_key,
                    actor_id=f"red_{index}_{imprint_key}",
                    seed=behavior_seed if behavior_seed is not None else seed,
                ),
                skill_profile=skill_profile,
            )
            actors.append(built.actor)
            participants.append(built.participant)
        return actors, participants

    def _active_character(
        self,
        build: StartingImprintBuild,
        *,
        actor_id: str,
        name: str,
        team: str,
        skill_profile: str,
    ) -> dict[str, Any]:
        by_id: dict[str, dict[str, Any]] = {}
        equipment: dict[str, str] = {}
        occupied_slots: set[str] = set()
        for base_id in build.item_base_ids:
            target_slot = self._starting_item_slot(base_id, occupied_slots)
            item = self._runtime_item(build, base_id=base_id, actor_id=actor_id, target_slot=target_slot)
            item_id = str(item["item_id"])
            slot = str(item["slot"])
            by_id[item_id] = item
            occupied_slots.add(slot)
            if slot not in equipment:
                equipment[slot] = item_id

        return {
            "char_id": actor_id,
            "user_id": "00000000-0000-0000-0000-000000000000",
            "bio": {"name": name},
            "location": {"current": "admin-ai-testing"},
            "vitals": {},
            "attributes": build.attributes,
            "skills": {skill_key: {"xp": xp} for skill_key, xp in self._skill_xp(build, skill_profile).items()},
            "symbiote": {"name": "SIM", "team": team},
            "items": {
                "layout": {"equipment": equipment, "belt": {}},
                "by_id": by_id,
            },
        }

    @staticmethod
    def _skill_xp(build: StartingImprintBuild, skill_profile: str) -> dict[str, float]:
        if skill_profile == STARTER_SKILL_PROFILE_MAXED_EXISTING:
            return {skill_key: 1.0 for skill_key in build.skill_xp}
        return dict(build.skill_xp)

    def _runtime_item(
        self,
        build: StartingImprintBuild,
        *,
        base_id: str,
        actor_id: str,
        target_slot: str | None = None,
    ) -> dict[str, Any]:
        item_id = f"{actor_id}:{base_id}"
        item = self.items.generate_runtime_item(
            ItemGenerationRequestDTO(
                generation_mode="runtime",
                base_id=base_id,
                target_slot=target_slot,
                rarity_tier=0,
                affix_count=0,
                affix_step_count=1,
                runtime_metadata={
                    "owner_key": actor_id,
                    "starting_imprint": build.imprint_key,
                    "runtime_item_id": item_id,
                },
                source_context={"starting_imprint": build.imprint_key},
                source="combat_simulation",
                origin_ref=ItemOriginRefDTO(
                    origin_type="system",
                    origin_ref=f"combat-simulation:{build.imprint_key}:{base_id}",
                    seed=f"{build.imprint_key}:{base_id}",
                ),
            )
        ).model_copy(update={"instance_id": item_id})
        data = item.model_dump(mode="json")
        mechanics = dict(data.get("mechanics") or {})
        mechanics.setdefault("base_id", item.base_id)
        mechanics.setdefault("item_type", item.item_type)
        mechanics.setdefault("slot", item.slot)
        mechanics.setdefault("valid_slots", item.valid_slots)
        mechanics.setdefault("power", item.power)
        mechanics.setdefault("damage_spread", item.damage_spread)
        mechanics.setdefault("implicit_bonuses", dict(item.implicit_bonuses))
        mechanics.setdefault("bonuses", dict(item.bonuses))
        mechanics.setdefault("triggers", list(item.triggers))
        mechanics.setdefault("tags", list(item.narrative_tags))
        data.update(
            {
                "item_id": item_id,
                "mechanics": mechanics,
                "related_skill": item.metadata.get("related_skill"),
                "armor_class": item.metadata.get("armor_class"),
                "tags": list(item.narrative_tags),
            }
        )
        return data

    def _starting_item_slot(self, base_id: str, occupied_slots: set[str]) -> str | None:
        base = self.items.catalog.get_base_item(base_id)
        if base is None:
            return None
        base_slot = str(base.slot)
        if base_slot not in occupied_slots:
            return base_slot
        for extra_slot in base.extra_slots:
            slot = str(extra_slot)
            if slot not in occupied_slots:
                return slot
        return base_slot

    @staticmethod
    def _hydrate_resources(actor: ActorSnapshot) -> None:
        if actor.stats is None:
            return
        max_hp = max(1, int(round(float(actor.stats.mods.hp or 0.0))))
        max_en = max(1, int(round(float(actor.stats.mods.en or 0.0))))
        max_stamina = max(1, int(round(float(actor.stats.mods.stamina or 0.0))))
        actor.meta.max_hp = max_hp
        actor.meta.hp = max_hp
        actor.meta.max_en = max_en
        actor.meta.en = max_en
        actor.meta.max_stamina = max_stamina
        actor.meta.stamina = max_stamina

    @staticmethod
    def _participant(
        actor: ActorSnapshot,
        build: StartingImprintBuild,
        known_feints: list[str],
        *,
        skill_profile: str,
    ) -> dict[str, Any]:
        stats = actor.stats.mods if actor.stats else None
        evasion = min(float(stats.evasion), float(stats.dodge_cap)) if stats else 0.0
        combat_stats = {
            "damage": round(float(stats.main_hand_damage_base), 2) if stats else 0.0,
            "hp_regen": round(float(stats.hp_regen), 3) if stats else 0.0,
            "armor": round(float(stats.armor), 2) if stats else 0.0,
            "physical_resistance": round(float(stats.physical_resistance), 3) if stats else 0.0,
            "evasion": round(evasion, 3),
            "parry": round(float(stats.parry), 3) if stats else 0.0,
            "block": round(float(stats.block), 3) if stats else 0.0,
            "accuracy_mod": round(float(stats.main_hand_accuracy), 3) if stats else 0.0,
            "crit": round(float(stats.main_hand_crit_chance), 3) if stats else 0.0,
        }
        gear_score = (
            CharacterGearScoreCalculator.calculate_breakdown_from_calculated(
                stats.model_dump(mode="json"),
                skill_score=CharacterGearScoreCalculator.calculate_skill_score(actor.skills),
            )
            if stats
            else {"total": 1, "offense": 0.0, "defense": 0.0, "resources": 0.0, "skills": 0.0, "utility": 0.0}
        )
        return {
            "actor_id": str(actor.meta.id),
            "label": actor.meta.name,
            "team": actor.meta.team,
            "type": actor.meta.type,
            "ai_archetype": actor.meta.ai_archetype,
            "behavior_profile": actor.meta.ai_behavior_profile,
            "start_hp": actor.meta.max_hp,
            "imprint_key": build.imprint_key,
            "imprint_title": build.title,
            "analytics_key": build.imprint_key,
            "combat_style": build.combat_style,
            "armor_pack": build.armor_pack,
            "item_base_ids": list(build.item_base_ids),
            "skill_keys": list(build.skill_keys),
            "skill_profile": skill_profile,
            "skills": dict(actor.skills),
            "known_feints": known_feints,
            "combat_stats": combat_stats,
            "gear_score": gear_score,
        }


def all_starting_imprint_keys() -> tuple[str, ...]:
    return tuple(STARTING_IMPRINTS)


def _starter_behavior_profile(*, imprint_key: str, actor_id: str, seed: int | None = None) -> str:
    return STARTER_SIMULATION_BEHAVIOR_PROFILES[0]


def random_starter_5v5_imprints(
    *,
    seed: int,
    pool: tuple[str, ...] = DEFAULT_STARTER_SIMULATION_IMPRINTS,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return random_starter_roster_imprints(seed=seed, pool=pool, min_team_size=5, max_team_size=5)


def random_starter_roster_imprints(
    *,
    seed: int,
    pool: tuple[str, ...] = DEFAULT_STARTER_SIMULATION_IMPRINTS,
    min_team_size: int = 5,
    max_team_size: int = 5,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if min_team_size < 1 or max_team_size < min_team_size:
        raise ValueError("Invalid starter simulation team size range")
    if max_team_size * 2 > len(pool):
        raise ValueError("Starter simulation team size cannot exceed half of the imprint pool")
    rng = random.Random(seed)
    shuffled = list(pool)
    rng.shuffle(shuffled)
    team_size = rng.randint(min_team_size, max_team_size)
    return tuple(shuffled[:team_size]), tuple(shuffled[team_size : team_size * 2])


__all__ = [
    "DEFAULT_STARTER_SIMULATION_IMPRINTS",
    "STARTER_SKILL_PROFILE_BASELINE",
    "STARTER_SKILL_PROFILE_MAXED_EXISTING",
    "STARTER_5V5_BLUE",
    "STARTER_5V5_RED",
    "StartingImprintSimulationActor",
    "StartingImprintSimulationActorBuilder",
    "all_starting_imprint_keys",
    "random_starter_5v5_imprints",
    "random_starter_roster_imprints",
]
