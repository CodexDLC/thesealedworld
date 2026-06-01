from src.backend.features.monsters.runtime.encounter_profiles import (
    MONSTER_ENCOUNTER_PROFILES,
    get_monster_encounter_profile,
)


def test_rat_swarm_profiles_cover_kind_and_difficulty_matrix() -> None:
    profiles = MONSTER_ENCOUNTER_PROFILES["rat_swarm"]

    assert set(profiles) == {"ordinary", "guard", "boss"}
    for kind_profiles in profiles.values():
        assert set(kind_profiles) == {"easy", "normal", "hard"}


def test_goblin_horde_profiles_cover_kind_and_difficulty_matrix() -> None:
    profiles = MONSTER_ENCOUNTER_PROFILES["goblin_tribe"]

    assert set(profiles) == {"ordinary", "guard", "boss"}
    for kind_profiles in profiles.values():
        assert set(kind_profiles) == {"easy", "normal", "hard"}


def test_wolf_pack_profiles_cover_kind_and_difficulty_matrix() -> None:
    profiles = MONSTER_ENCOUNTER_PROFILES["wolf_pack"]

    assert set(profiles) == {"ordinary", "guard", "boss"}
    for kind_profiles in profiles.values():
        assert set(kind_profiles) == {"easy", "normal", "hard"}


def test_bandit_gang_profiles_cover_kind_and_difficulty_matrix() -> None:
    profiles = MONSTER_ENCOUNTER_PROFILES["bandit_gang"]

    assert set(profiles) == {"ordinary", "guard", "boss"}
    for kind_profiles in profiles.values():
        assert set(kind_profiles) == {"easy", "normal", "hard"}


def test_ordinary_easy_profiles_are_small_minion_to_veteran_placeholders() -> None:
    for family_id in ("rat_swarm", "goblin_tribe", "wolf_pack", "bandit_gang"):
        profile = get_monster_encounter_profile(family_id, "ordinary", "easy")

        assert profile is not None
        assert profile["budget_multiplier"] == 0.75
        assert profile["min_units"] == 1
        assert profile["max_units"] == 2
        assert profile["start_role"] == "minion"
        assert profile["allowed_roles"] == ["minion", "veteran"]
        assert profile["role_caps"] == {"minion": 2, "veteran": 2, "elite": 0, "boss": 0}
        assert profile["upgrade_order"] == ["veteran"]


def test_ordinary_normal_profiles_are_small_duos_with_one_elite_cap() -> None:
    for family_id in ("rat_swarm", "goblin_tribe", "wolf_pack", "bandit_gang"):
        profile = get_monster_encounter_profile(family_id, "ordinary", "normal")

        assert profile is not None
        assert profile["min_units"] == 1
        assert profile["max_units"] == 2
        assert profile["allowed_roles"] == ["minion", "veteran", "elite"]
        assert profile["role_caps"]["elite"] == 1
        assert profile["role_caps"]["boss"] == 0


def test_ordinary_hard_profiles_are_small_veteran_to_elite_placeholders() -> None:
    for family_id in ("rat_swarm", "goblin_tribe", "wolf_pack", "bandit_gang"):
        profile = get_monster_encounter_profile(family_id, "ordinary", "hard")

        assert profile is not None
        assert profile["budget_multiplier"] == 1.25
        assert profile["min_units"] == 1
        assert profile["max_units"] == 2
        assert profile["start_role"] == "veteran"
        assert profile["allowed_roles"] == ["veteran", "elite"]
        assert profile["role_caps"] == {"minion": 0, "veteran": 2, "elite": 2, "boss": 0}


def test_rat_swarm_guard_profiles_require_guard_roles_without_boss() -> None:
    easy = get_monster_encounter_profile("rat_swarm", "guard", "easy")
    normal = get_monster_encounter_profile("rat_swarm", "guard", "normal")
    hard = get_monster_encounter_profile("rat_swarm", "guard", "hard")

    assert easy is not None
    assert normal is not None
    assert hard is not None
    assert easy["required_roles"] == ["veteran"]
    assert normal["required_roles"] == ["veteran"]
    assert hard["required_roles"] == ["elite"]
    assert easy["role_caps"]["boss"] == 0
    assert normal["role_caps"]["boss"] == 0
    assert hard["role_caps"]["boss"] == 0


def test_rat_swarm_boss_easy_uses_elite_and_veteran_before_true_bosses() -> None:
    profile = get_monster_encounter_profile("rat_swarm", "boss", "easy")

    assert profile is not None
    assert profile["required_roles"] == ["veteran", "elite"]
    assert profile["allowed_roles"] == ["veteran", "elite"]
    assert profile["role_caps"]["boss"] == 0


def test_rat_swarm_boss_normal_and_hard_require_true_boss() -> None:
    normal = get_monster_encounter_profile("rat_swarm", "boss", "normal")
    hard = get_monster_encounter_profile("rat_swarm", "boss", "hard")

    assert normal is not None
    assert hard is not None
    assert normal["required_roles"] == ["boss"]
    assert hard["required_roles"] == ["boss"]
    assert normal["role_caps"]["boss"] == 1
    assert hard["role_caps"]["boss"] == 1
    assert hard["max_units"] > normal["min_units"]


def test_goblin_horde_guard_and_boss_keep_lower_body_counts() -> None:
    guard_easy = get_monster_encounter_profile("goblin_tribe", "guard", "easy")
    guard_normal = get_monster_encounter_profile("goblin_tribe", "guard", "normal")
    guard_hard = get_monster_encounter_profile("goblin_tribe", "guard", "hard")
    boss_easy = get_monster_encounter_profile("goblin_tribe", "boss", "easy")
    boss_normal = get_monster_encounter_profile("goblin_tribe", "boss", "normal")
    boss_hard = get_monster_encounter_profile("goblin_tribe", "boss", "hard")

    assert guard_easy is not None
    assert guard_normal is not None
    assert guard_hard is not None
    assert boss_easy is not None
    assert boss_normal is not None
    assert boss_hard is not None
    assert guard_easy["min_units"] == 2
    assert guard_easy["max_units"] == 4
    assert guard_easy["required_roles"] == ["veteran"]
    assert guard_normal["min_units"] == 2
    assert guard_normal["max_units"] == 5
    assert guard_normal["role_caps"]["elite"] == 1
    assert guard_hard["min_units"] == 3
    assert guard_hard["max_units"] == 5
    assert guard_hard["required_roles"] == ["elite"]
    assert boss_easy["min_units"] == 2
    assert boss_easy["max_units"] == 3
    assert boss_easy["required_roles"] == ["veteran", "elite"]
    assert boss_easy["role_caps"]["boss"] == 0
    assert boss_normal["min_units"] == 2
    assert boss_normal["max_units"] == 4
    assert boss_normal["required_roles"] == ["boss"]
    assert boss_hard["min_units"] == 3
    assert boss_hard["max_units"] == 5
    assert boss_hard["role_caps"]["boss"] == 1


def test_wolf_pack_guard_and_boss_keep_pack_scale() -> None:
    guard_easy = get_monster_encounter_profile("wolf_pack", "guard", "easy")
    guard_normal = get_monster_encounter_profile("wolf_pack", "guard", "normal")
    guard_hard = get_monster_encounter_profile("wolf_pack", "guard", "hard")
    boss_easy = get_monster_encounter_profile("wolf_pack", "boss", "easy")
    boss_normal = get_monster_encounter_profile("wolf_pack", "boss", "normal")
    boss_hard = get_monster_encounter_profile("wolf_pack", "boss", "hard")

    assert guard_easy is not None
    assert guard_normal is not None
    assert guard_hard is not None
    assert boss_easy is not None
    assert boss_normal is not None
    assert boss_hard is not None
    assert guard_easy["min_units"] == 2
    assert guard_easy["max_units"] == 3
    assert guard_easy["required_roles"] == ["veteran"]
    assert guard_normal["min_units"] == 2
    assert guard_normal["max_units"] == 4
    assert guard_normal["role_caps"]["elite"] == 1
    assert guard_hard["min_units"] == 2
    assert guard_hard["max_units"] == 4
    assert guard_hard["required_roles"] == ["elite"]
    assert boss_easy["min_units"] == 2
    assert boss_easy["max_units"] == 3
    assert boss_easy["required_roles"] == ["veteran", "elite"]
    assert boss_easy["role_caps"]["boss"] == 0
    assert boss_normal["min_units"] == 2
    assert boss_normal["max_units"] == 4
    assert boss_normal["required_roles"] == ["boss"]
    assert boss_hard["min_units"] == 3
    assert boss_hard["max_units"] == 4
    assert boss_hard["role_caps"]["boss"] == 1


def test_bandit_gang_guard_and_boss_stay_capped_at_three() -> None:
    guard_easy = get_monster_encounter_profile("bandit_gang", "guard", "easy")
    guard_normal = get_monster_encounter_profile("bandit_gang", "guard", "normal")
    guard_hard = get_monster_encounter_profile("bandit_gang", "guard", "hard")
    boss_easy = get_monster_encounter_profile("bandit_gang", "boss", "easy")
    boss_normal = get_monster_encounter_profile("bandit_gang", "boss", "normal")
    boss_hard = get_monster_encounter_profile("bandit_gang", "boss", "hard")

    assert guard_easy is not None
    assert guard_normal is not None
    assert guard_hard is not None
    assert boss_easy is not None
    assert boss_normal is not None
    assert boss_hard is not None
    assert guard_easy["min_units"] == 1
    assert guard_easy["max_units"] == 3
    assert guard_easy["required_roles"] == ["veteran"]
    assert guard_normal["min_units"] == 2
    assert guard_normal["max_units"] == 3
    assert guard_normal["role_caps"]["elite"] == 1
    assert guard_hard["min_units"] == 2
    assert guard_hard["max_units"] == 3
    assert guard_hard["required_roles"] == ["elite"]
    assert boss_easy["min_units"] == 2
    assert boss_easy["max_units"] == 3
    assert boss_easy["required_roles"] == ["veteran", "elite"]
    assert boss_easy["role_caps"]["boss"] == 0
    assert boss_normal["min_units"] == 2
    assert boss_normal["max_units"] == 3
    assert boss_normal["required_roles"] == ["boss"]
    assert boss_hard["min_units"] == 2
    assert boss_hard["max_units"] == 3
    assert boss_hard["role_caps"]["boss"] == 1


def test_get_monster_encounter_profile_returns_copy() -> None:
    first = get_monster_encounter_profile("rat_swarm", "ordinary", "easy")
    second = get_monster_encounter_profile("rat_swarm", "ordinary", "easy")
    assert first is not None
    assert second is not None

    first["allowed_roles"].append("elite")
    first["role_caps"]["elite"] = 99

    assert second["allowed_roles"] == ["minion", "veteran"]
    assert second["role_caps"]["elite"] == 0
