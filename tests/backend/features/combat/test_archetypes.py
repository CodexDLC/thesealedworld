"""Tests for archetype-aware policy loading (PR3)."""

from __future__ import annotations

import pytest

from src.backend.features.combat.dto.actor import (
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    ActorStats,
    FeintHandDTO,
)
from src.backend.features.combat.runtime.ai.archetypes import (
    Archetype,
    archetype_policy_filename,
)
from src.backend.features.combat.runtime.ai.brain import MonsterCombatBrain
from src.backend.features.combat.runtime.ai.policy_store import PolicyStore
from src.backend.features.monsters.runtime.ai_archetype import resolve_monster_ai_archetype
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


def _bot(ai_archetype: str = "balanced") -> ActorSnapshot:
    return ActorSnapshot(
        meta=ActorMetaDTO(
            id="bot",
            name="bot",
            type="monster",
            team="red",
            is_ai=True,
            hp=100,
            max_hp=100,
            en=10,
            max_en=10,
            stamina=50,
            max_stamina=50,
            tactics=0,
            tokens={},
            feints=FeintHandDTO(hand={}, arsenal=[]),
            ai_archetype=ai_archetype,
        ),
        raw=ActorRawDTO(),
        skills={},
        loadout=ActorLoadoutDTO(),
        stats=ActorStats(mods=CombatModifiersDTO(), skills=CombatSkillsDTO()),
    )


# ---------------------------------------------------------------------------
# Archetype enum coercion
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_archetype_coerce_known_values() -> None:
    assert Archetype.coerce("berserker") is Archetype.BERSERKER
    assert Archetype.coerce("DUELIST") is Archetype.DUELIST
    assert Archetype.coerce("  bulwark  ") is Archetype.BULWARK


@pytest.mark.unit
def test_archetype_coerce_unknown_falls_back_to_balanced() -> None:
    assert Archetype.coerce(None) is Archetype.BALANCED
    assert Archetype.coerce("") is Archetype.BALANCED
    assert Archetype.coerce("nonexistent_archetype") is Archetype.BALANCED


@pytest.mark.unit
def test_archetype_policy_filename_is_stable() -> None:
    assert archetype_policy_filename(Archetype.BERSERKER) == "archetype_berserker.json"
    assert archetype_policy_filename(Archetype.TACTICIAN) == "archetype_tactician.json"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("variant_id", "family_archetype", "role", "expected"),
    [
        ("rat_brute", "beast", "boss", "berserker"),
        ("bandit_billhook", "humanoid", "veteran", "duelist"),
        ("goblin_scrapguard", "humanoid", "veteran", "bulwark"),
        ("goblin_trapmaster", "humanoid", "elite", "tactician"),
        ("north_stasis_sovereign", "unknown", "boss", "bulwark"),
    ],
)
def test_monster_ai_archetype_resolver_uses_variant_mapping(
    variant_id: str,
    family_archetype: str,
    role: str,
    expected: str,
) -> None:
    assert resolve_monster_ai_archetype(variant_id, family_archetype, role) == expected


@pytest.mark.unit
def test_monster_ai_archetype_resolver_keeps_unmapped_variants_balanced() -> None:
    assert resolve_monster_ai_archetype("sewer_rat", "beast", "minion") == "balanced"
    assert resolve_monster_ai_archetype("unknown_variant", "humanoid", "boss") == "balanced"


@pytest.mark.unit
def test_monster_ai_archetype_resolver_uses_family_role_fallback_without_variant_id() -> None:
    assert resolve_monster_ai_archetype(None, "humanoid", "boss") == "tactician"
    assert resolve_monster_ai_archetype("", "beast", "veteran") == "duelist"


# ---------------------------------------------------------------------------
# PolicyStore.load(archetype=...)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_policy_store_balanced_archetype_returns_base_policy() -> None:
    store = PolicyStore()
    base = store.load()
    balanced = store.load(archetype="balanced")
    assert balanced.get("expected_damage") == pytest.approx(base.get("expected_damage"))


@pytest.mark.unit
def test_policy_store_unknown_archetype_falls_back_to_base_policy() -> None:
    store = PolicyStore()
    base = store.load()
    unknown = store.load(archetype="not_a_real_archetype")
    assert unknown.get("anti_parry") == pytest.approx(base.get("anti_parry"))


@pytest.mark.unit
def test_policy_store_berserker_overrides_aggression_keys() -> None:
    store = PolicyStore()
    base = store.load()
    berserker = store.load(archetype="berserker")

    assert berserker.get("expected_damage") > base.get("expected_damage")
    assert berserker.get("finishable") > base.get("finishable")
    assert berserker.get("defense") < base.get("defense")
    # Berserker explicitly does not avoid prep threats.
    assert berserker.get("prep_threat_penalty") == pytest.approx(0.0)


@pytest.mark.unit
def test_policy_store_tactician_emphasises_control_and_dispel() -> None:
    store = PolicyStore()
    base = store.load()
    tactician = store.load(archetype="tactician")
    assert tactician.get("control") > base.get("control")
    assert tactician.get("dispel_prep") > base.get("dispel_prep")
    assert tactician.get("debuff") > base.get("debuff")


@pytest.mark.unit
def test_policy_store_archetype_merge_preserves_unspecified_keys() -> None:
    """Archetype JSONs only list overrides — the merge must fill in everything
    else from the base policy. Without this, the scorer would see missing
    keys defaulting to 0.0 and behave nothing like ``balanced``."""
    store = PolicyStore()
    base = store.load()
    duelist = store.load(archetype="duelist")
    # ``finishable`` is NOT overridden in archetype_duelist.json.
    assert duelist.get("finishable") == pytest.approx(base.get("finishable"))
    # ``token_cost`` is also not overridden.
    assert duelist.get("token_cost") == pytest.approx(base.get("token_cost"))


@pytest.mark.unit
def test_policy_store_archetype_metadata_records_archetype_label() -> None:
    store = PolicyStore()
    bulwark = store.load(archetype="bulwark")
    assert bulwark.metadata.get("archetype") == "bulwark"


# ---------------------------------------------------------------------------
# Brain wires archetype through bot.meta.ai_archetype
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_brain_resolves_archetype_from_bot_meta() -> None:
    brain = MonsterCombatBrain()
    base = PolicyStore().load()
    berserker_policy = brain._policy_for_bot(_bot("berserker"))
    balanced_policy = brain._policy_for_bot(_bot("balanced"))

    assert berserker_policy.get("expected_damage") > base.get("expected_damage")
    assert balanced_policy.get("expected_damage") == pytest.approx(base.get("expected_damage"))


@pytest.mark.unit
def test_brain_policy_override_bypasses_archetype_resolution() -> None:
    """An explicit ``policy=`` on the brain constructor must short-circuit
    archetype lookup — used by tests and tuning to pin behaviour."""
    from src.backend.features.combat.runtime.ai.policy import Policy

    custom = Policy.with_defaults({"expected_damage": 999.0})
    brain = MonsterCombatBrain(policy=custom)
    resolved = brain._policy_for_bot(_bot("berserker"))
    assert resolved.get("expected_damage") == pytest.approx(999.0)
