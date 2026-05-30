"""Build simulation actors from real character starting imprints."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from src.backend.features.character.resources.starting_imprints import STARTING_IMPRINTS, StartingImprintDefinition
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
    "starter_breaker_01",
    "starter_duelist_01",
    "starter_dual_blades_01",
    "starter_hunter_01",
    "starter_archer_01",
    "starter_staff_01",
    "starter_heavy_guard_01",
    "starter_tactician_01",
    "starter_rift_survivor_01",
)
BALANCE_SIMULATION_IMPRINTS: dict[str, StartingImprintDefinition] = {
    "sim_dual_light_01": StartingImprintDefinition(
        imprint_key="sim_dual_light_01",
        title="Баланс: два клинка light",
        primary_stats=("agility", "strength", "perception", "prediction"),
        combat_style="dual_light",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_fencing", 0.15),
            ("skill_dual_wield", 0.15),
            ("skill_parrying", 0.10),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "dual_wield", "light"),
        description="Балансный тестовый слепок: два клинка в лёгкой броне.",
    ),
    "sim_dual_medium_01": StartingImprintDefinition(
        imprint_key="sim_dual_medium_01",
        title="Баланс: два клинка medium",
        primary_stats=("agility", "strength", "endurance", "perception"),
        combat_style="dual_light",
        armor_pack="medium_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_fencing", 0.15),
            ("skill_dual_wield", 0.15),
            ("skill_parrying", 0.10),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "dual_wield", "medium"),
        description="Балансный тестовый слепок: два клинка в средней броне.",
    ),
    "sim_dual_heavy_01": StartingImprintDefinition(
        imprint_key="sim_dual_heavy_01",
        title="Баланс: два клинка heavy",
        primary_stats=("strength", "agility", "endurance", "perception"),
        combat_style="dual_light",
        armor_pack="heavy_full",
        utility_pack="frontline_basic",
        skill_xp=(
            ("skill_fencing", 0.15),
            ("skill_dual_wield", 0.15),
            ("skill_parrying", 0.10),
            ("skill_heavy_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "dual_wield", "heavy"),
        description="Балансный тестовый слепок: два клинка в тяжёлой броне.",
    ),
    "sim_twohand_light_01": StartingImprintDefinition(
        imprint_key="sim_twohand_light_01",
        title="Баланс: двуруч light",
        primary_stats=("strength", "agility", "perception", "endurance"),
        combat_style="two_handed_impact",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_macing", 0.15),
            ("skill_two_handed", 0.15),
            ("skill_tactics", 0.10),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "two_handed", "light"),
        description="Балансный тестовый слепок: двуручное ударное оружие в лёгкой броне.",
    ),
    "sim_twohand_medium_01": StartingImprintDefinition(
        imprint_key="sim_twohand_medium_01",
        title="Баланс: двуруч medium",
        primary_stats=("strength", "agility", "endurance", "mental"),
        combat_style="two_handed_impact",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_macing", 0.15),
            ("skill_two_handed", 0.15),
            ("skill_tactics", 0.10),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "two_handed", "medium"),
        description="Балансный тестовый слепок: двуручное ударное оружие в средней броне.",
    ),
    "sim_twohand_heavy_01": StartingImprintDefinition(
        imprint_key="sim_twohand_heavy_01",
        title="Баланс: двуруч heavy",
        primary_stats=("strength", "agility", "endurance", "mental"),
        combat_style="two_handed_impact",
        armor_pack="heavy_full",
        utility_pack="frontline_basic",
        skill_xp=(
            ("skill_macing", 0.15),
            ("skill_two_handed", 0.15),
            ("skill_tactics", 0.10),
            ("skill_heavy_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "two_handed", "heavy"),
        description="Балансный тестовый слепок: двуручное ударное оружие в тяжёлой броне.",
    ),
    "sim_polearm_light_01": StartingImprintDefinition(
        imprint_key="sim_polearm_light_01",
        title="Баланс: полеарм light",
        primary_stats=("strength", "agility", "perception", "prediction"),
        combat_style="polearm_reach",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_polearms", 0.15),
            ("skill_two_handed", 0.15),
            ("skill_tactics", 0.10),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "polearm", "light"),
        description="Балансный тестовый слепок: древковое оружие в лёгкой броне.",
    ),
    "sim_polearm_medium_01": StartingImprintDefinition(
        imprint_key="sim_polearm_medium_01",
        title="Баланс: полеарм medium",
        primary_stats=("strength", "agility", "endurance", "perception"),
        combat_style="polearm_reach",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_polearms", 0.15),
            ("skill_two_handed", 0.15),
            ("skill_tactics", 0.10),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "polearm", "medium"),
        description="Балансный тестовый слепок: древковое оружие в средней броне.",
    ),
    "sim_polearm_heavy_01": StartingImprintDefinition(
        imprint_key="sim_polearm_heavy_01",
        title="Баланс: полеарм heavy",
        primary_stats=("strength", "agility", "endurance", "mental"),
        combat_style="polearm_reach",
        armor_pack="heavy_full",
        utility_pack="frontline_basic",
        skill_xp=(
            ("skill_polearms", 0.15),
            ("skill_two_handed", 0.15),
            ("skill_tactics", 0.10),
            ("skill_heavy_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "polearm", "heavy"),
        description="Балансный тестовый слепок: древковое оружие в тяжёлой броне.",
    ),
    "sim_shield_light_01": StartingImprintDefinition(
        imprint_key="sim_shield_light_01",
        title="Баланс: щит light",
        primary_stats=("strength", "agility", "perception", "endurance"),
        combat_style="one_handed_shield",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_swords", 0.15),
            ("skill_shield_mastery", 0.15),
            ("skill_parrying", 0.10),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "shield", "light"),
        description="Балансный тестовый слепок: меч и щит в лёгкой броне.",
    ),
    "sim_shield_medium_01": StartingImprintDefinition(
        imprint_key="sim_shield_medium_01",
        title="Баланс: щит medium",
        primary_stats=("strength", "agility", "endurance", "perception"),
        combat_style="one_handed_shield",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_swords", 0.15),
            ("skill_shield_mastery", 0.15),
            ("skill_parrying", 0.10),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "shield", "medium"),
        description="Балансный тестовый слепок: меч и щит в средней броне.",
    ),
    "sim_shield_heavy_01": StartingImprintDefinition(
        imprint_key="sim_shield_heavy_01",
        title="Баланс: щит heavy",
        primary_stats=("strength", "agility", "endurance", "mental"),
        combat_style="one_handed_shield",
        armor_pack="heavy_full",
        utility_pack="frontline_basic",
        skill_xp=(
            ("skill_swords", 0.15),
            ("skill_shield_mastery", 0.15),
            ("skill_parrying", 0.10),
            ("skill_heavy_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "shield", "heavy"),
        description="Балансный тестовый слепок: меч и щит в тяжёлой броне.",
    ),
    "sim_mace_shield_medium_01": StartingImprintDefinition(
        imprint_key="sim_mace_shield_medium_01",
        title="Баланс: булава+щит medium",
        primary_stats=("strength", "agility", "endurance", "mental"),
        combat_style="mace_shield",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_macing", 0.15),
            ("skill_shield_mastery", 0.15),
            ("skill_parrying", 0.10),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "shield", "macing", "medium"),
        description="Балансный тестовый слепок: булава и щит в средней броне.",
    ),
    "sim_mace_shield_heavy_01": StartingImprintDefinition(
        imprint_key="sim_mace_shield_heavy_01",
        title="Баланс: булава+щит heavy",
        primary_stats=("strength", "agility", "endurance", "mental"),
        combat_style="mace_shield",
        armor_pack="heavy_full",
        utility_pack="frontline_basic",
        skill_xp=(
            ("skill_macing", 0.15),
            ("skill_shield_mastery", 0.15),
            ("skill_parrying", 0.10),
            ("skill_heavy_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "shield", "macing", "heavy"),
        description="Балансный тестовый слепок: булава и щит в тяжёлой броне.",
    ),
    "sim_staff_light_01": StartingImprintDefinition(
        imprint_key="sim_staff_light_01",
        title="Баланс: посох light",
        primary_stats=("strength", "agility", "perception", "prediction"),
        combat_style="two_handed_reach",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_polearms", 0.15),
            ("skill_two_handed", 0.15),
            ("skill_pathfinder", 0.10),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "staff", "light"),
        description="Балансный тестовый слепок: посох в лёгкой броне.",
    ),
    "sim_staff_medium_01": StartingImprintDefinition(
        imprint_key="sim_staff_medium_01",
        title="Баланс: посох medium",
        primary_stats=("strength", "agility", "endurance", "perception"),
        combat_style="two_handed_reach",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_polearms", 0.15),
            ("skill_two_handed", 0.15),
            ("skill_pathfinder", 0.10),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "staff", "medium"),
        description="Балансный тестовый слепок: посох в средней броне.",
    ),
    "sim_staff_heavy_01": StartingImprintDefinition(
        imprint_key="sim_staff_heavy_01",
        title="Баланс: посох heavy",
        primary_stats=("strength", "agility", "endurance", "mental"),
        combat_style="two_handed_reach",
        armor_pack="heavy_full",
        utility_pack="frontline_basic",
        skill_xp=(
            ("skill_polearms", 0.15),
            ("skill_two_handed", 0.15),
            ("skill_pathfinder", 0.10),
            ("skill_heavy_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "staff", "heavy"),
        description="Балансный тестовый слепок: посох в тяжёлой броне.",
    ),
    "sim_bow_light_01": StartingImprintDefinition(
        imprint_key="sim_bow_light_01",
        title="Баланс: лук light",
        primary_stats=("agility", "strength", "perception", "prediction"),
        combat_style="longbow_quiver",
        armor_pack="light_full",
        utility_pack="mobile_basic",
        skill_xp=(
            ("skill_archery", 0.15),
            ("skill_ranged_combat", 0.15),
            ("skill_tactics", 0.10),
            ("skill_light_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "bow", "light"),
        description="Балансный тестовый слепок: лук в лёгкой броне.",
    ),
    "sim_bow_medium_01": StartingImprintDefinition(
        imprint_key="sim_bow_medium_01",
        title="Баланс: лук medium",
        primary_stats=("agility", "strength", "perception", "endurance"),
        combat_style="longbow_quiver",
        armor_pack="medium_full",
        utility_pack="field_basic",
        skill_xp=(
            ("skill_archery", 0.15),
            ("skill_ranged_combat", 0.15),
            ("skill_tactics", 0.10),
            ("skill_medium_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "bow", "medium"),
        description="Балансный тестовый слепок: лук в средней броне.",
    ),
    "sim_bow_heavy_01": StartingImprintDefinition(
        imprint_key="sim_bow_heavy_01",
        title="Баланс: лук heavy",
        primary_stats=("agility", "strength", "endurance", "perception"),
        combat_style="longbow_quiver",
        armor_pack="heavy_full",
        utility_pack="frontline_basic",
        skill_xp=(
            ("skill_archery", 0.15),
            ("skill_ranged_combat", 0.15),
            ("skill_tactics", 0.10),
            ("skill_heavy_armor", 0.10),
        ),
        lore_tags=("simulation_balance", "bow", "heavy"),
        description="Негативный контроль: лук в тяжёлой броне.",
    ),
}
BALANCE_TEST_SIMULATION_IMPRINTS: tuple[str, ...] = (
    *DEFAULT_STARTER_SIMULATION_IMPRINTS,
    *tuple(BALANCE_SIMULATION_IMPRINTS),
)
STARTER_SKILL_PROFILE_BASELINE = "baseline"
STARTER_SKILL_PROFILE_MAXED_EXISTING = "maxed_existing_skills"

STARTER_5V5_BLUE: tuple[str, ...] = DEFAULT_STARTER_SIMULATION_IMPRINTS[:5]
STARTER_5V5_RED: tuple[str, ...] = DEFAULT_STARTER_SIMULATION_IMPRINTS[5:]

STARTER_SIMULATION_NAMES: dict[str, str] = {
    "starter_guard_01": "Ada Guard",
    "starter_breaker_01": "Borin Breaker",
    "starter_duelist_01": "Cira Duelist",
    "starter_dual_blades_01": "Dax Twinblades",
    "starter_pathfinder_01": "Eli Pathfinder",
    "starter_hunter_01": "Fenn Hunter",
    "starter_archer_01": "Galen Archer",
    "starter_staff_01": "Hara Staff",
    "starter_heavy_guard_01": "Ivar Bulwark",
    "starter_tactician_01": "Juno Tactician",
    "starter_rift_survivor_01": "Kael Survivor",
}

STARTER_SIMULATION_ARCHETYPES: dict[str, str] = {
    "starter_guard_01": "bulwark",
    "starter_breaker_01": "berserker",
    "starter_duelist_01": "duelist",
    "starter_dual_blades_01": "duelist",
    "starter_pathfinder_01": "duelist",
    "starter_hunter_01": "duelist",
    "starter_archer_01": "duelist",
    "starter_staff_01": "balanced",
    "starter_heavy_guard_01": "bulwark",
    "starter_tactician_01": "tactician",
    "starter_rift_survivor_01": "balanced",
}
STARTER_SIMULATION_ARCHETYPES.update(
    {
        "sim_dual_light_01": "duelist",
        "sim_dual_medium_01": "duelist",
        "sim_dual_heavy_01": "duelist",
        "sim_twohand_light_01": "berserker",
        "sim_twohand_medium_01": "berserker",
        "sim_twohand_heavy_01": "berserker",
        "sim_polearm_light_01": "balanced",
        "sim_polearm_medium_01": "balanced",
        "sim_polearm_heavy_01": "balanced",
        "sim_shield_light_01": "bulwark",
        "sim_shield_medium_01": "bulwark",
        "sim_shield_heavy_01": "bulwark",
        "sim_mace_shield_medium_01": "bulwark",
        "sim_mace_shield_heavy_01": "bulwark",
        "sim_staff_light_01": "balanced",
        "sim_staff_medium_01": "balanced",
        "sim_staff_heavy_01": "balanced",
        "sim_bow_light_01": "duelist",
        "sim_bow_medium_01": "duelist",
        "sim_bow_heavy_01": "duelist",
    }
)


@dataclass(frozen=True, slots=True)
class StartingImprintSimulationActor:
    actor: ActorSnapshot
    participant: dict[str, Any]


class SimulationStartingImprintService(StartingImprintService):
    """Starting imprint service with simulation-only balance variants."""

    @staticmethod
    def get_definition(imprint_key: str) -> StartingImprintDefinition:
        if imprint_key in BALANCE_SIMULATION_IMPRINTS:
            return BALANCE_SIMULATION_IMPRINTS[imprint_key]
        return StartingImprintService.get_definition(imprint_key)


class StartingImprintSimulationActorBuilder:
    """Materialise real starter builds into combat ActorSnapshot objects."""

    def __init__(
        self,
        *,
        imprints: StartingImprintService | None = None,
        items: ItemFactory | None = None,
        combat_input: CharacterCombatActorInputBuilder | None = None,
    ) -> None:
        self.imprints = imprints or SimulationStartingImprintService()
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
                skill_profile=skill_profile,
            )
            actors.append(built.actor)
            participants.append(built.participant)
        for index, imprint_key in enumerate(red_imprints, start=1):
            built = self.build_actor(
                imprint_key,
                actor_id=f"red_{index}_{imprint_key}",
                team="red",
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
        for base_id in build.item_base_ids:
            item = self._runtime_item(build, base_id=base_id, actor_id=actor_id)
            item_id = str(item["item_id"])
            slot = str(item["slot"])
            by_id[item_id] = item
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

    def _runtime_item(self, build: StartingImprintBuild, *, base_id: str, actor_id: str) -> dict[str, Any]:
        item_id = f"{actor_id}:{base_id}"
        item = self.items.generate_runtime_item(
            ItemGenerationRequestDTO(
                generation_mode="runtime",
                base_id=base_id,
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
            "armor": round(float(stats.armor), 2) if stats else 0.0,
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
            "start_hp": actor.meta.max_hp,
            "imprint_key": build.imprint_key,
            "imprint_title": build.title,
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
    return tuple(STARTING_IMPRINTS) + tuple(BALANCE_SIMULATION_IMPRINTS)


def random_starter_5v5_imprints(
    *,
    seed: int,
    pool: tuple[str, ...] = BALANCE_TEST_SIMULATION_IMPRINTS,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return random_starter_roster_imprints(seed=seed, pool=pool, min_team_size=5, max_team_size=5)


def random_starter_roster_imprints(
    *,
    seed: int,
    pool: tuple[str, ...] = BALANCE_TEST_SIMULATION_IMPRINTS,
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
    "BALANCE_SIMULATION_IMPRINTS",
    "BALANCE_TEST_SIMULATION_IMPRINTS",
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
