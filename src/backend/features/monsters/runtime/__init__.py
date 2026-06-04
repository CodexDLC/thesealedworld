from __future__ import annotations

__all__ = [
    "ClanFactory",
    "MonsterGroupAssembler",
    "MonsterGroupAssembly",
    "MonsterHashContext",
    "MonsterClanGenerationBuilder",
    "MonsterCombatActorInputBuilder",
    "MonsterCombatMathModelBuilder",
    "MonsterPipelineProfile",
    "MONSTER_ENCOUNTER_PROFILES",
    "build_ai_profile",
    "build_balance",
    "build_generated_monster_template",
    "build_granted_abilities",
    "build_items",
    "build_member_tier",
    "build_meta",
    "build_scaled_attributes",
    "build_scaled_skills",
    "build_text_payload",
    "compute_context_hash",
    "compute_monster_context_hash",
    "compute_rift_context_hash",
    "compute_unique_clan_hash",
    "get_monster_encounter_profile",
    "normalize_tags",
    "normalized_monster_hash_tags",
]


def __getattr__(name: str) -> object:
    if name == "ClanFactory":
        from src.backend.features.monsters.runtime.clan_factory import ClanFactory

        return ClanFactory
    if name == "MonsterCombatActorInputBuilder":
        from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder

        return MonsterCombatActorInputBuilder
    if name in {"MonsterCombatMathModelBuilder", "MonsterPipelineProfile"}:
        from src.backend.features.monsters.runtime.combat_math_model import (
            MonsterCombatMathModelBuilder,
            MonsterPipelineProfile,
        )

        return {
            "MonsterCombatMathModelBuilder": MonsterCombatMathModelBuilder,
            "MonsterPipelineProfile": MonsterPipelineProfile,
        }[name]
    if name in {"MONSTER_ENCOUNTER_PROFILES", "get_monster_encounter_profile"}:
        from src.backend.features.monsters.runtime.encounter_profiles import (
            MONSTER_ENCOUNTER_PROFILES,
            get_monster_encounter_profile,
        )

        return {
            "MONSTER_ENCOUNTER_PROFILES": MONSTER_ENCOUNTER_PROFILES,
            "get_monster_encounter_profile": get_monster_encounter_profile,
        }[name]
    if name == "MonsterClanGenerationBuilder":
        from src.backend.features.monsters.runtime.generation_builder import MonsterClanGenerationBuilder

        return MonsterClanGenerationBuilder
    if name in {
        "build_ai_profile",
        "build_balance",
        "build_generated_monster_template",
        "build_granted_abilities",
        "build_items",
        "build_member_tier",
        "build_meta",
        "build_scaled_attributes",
        "build_scaled_skills",
        "build_text_payload",
    }:
        from src.backend.features.monsters.runtime import generation_fields

        return getattr(generation_fields, name)
    if name in {"MonsterGroupAssembler", "MonsterGroupAssembly"}:
        from src.backend.features.monsters.runtime.group_assembler import MonsterGroupAssembler, MonsterGroupAssembly

        return {
            "MonsterGroupAssembler": MonsterGroupAssembler,
            "MonsterGroupAssembly": MonsterGroupAssembly,
        }[name]
    if name in {
        "MonsterHashContext",
        "compute_context_hash",
        "compute_monster_context_hash",
        "compute_rift_context_hash",
        "compute_unique_clan_hash",
        "normalize_tags",
        "normalized_monster_hash_tags",
    }:
        from src.backend.features.monsters.runtime import hashing

        return getattr(hashing, name)
    raise AttributeError(name)
