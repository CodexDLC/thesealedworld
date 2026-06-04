from src.backend.features.monsters.resources.visuals import (
    build_clan_visual,
    build_member_visual,
    build_monster_visual_prompt,
    get_family_visual,
    version_generated_asset_url,
    version_visual_image_urls,
)


def test_family_visual_exposes_content_addressed_generated_target() -> None:
    visual = get_family_visual("rat_swarm")

    assert visual["status"] == "placeholder"
    assert visual["image_url"] == "/static/images/monsters/families/rat_swarm.svg"
    assert str(visual["storage_key"]).startswith("monsters/generated/families/")
    assert str(visual["generated_image_url"]).startswith("/static/generated-assets/monsters/generated/families/")
    assert str(visual["generated_image_url"]).endswith(".webp")
    assert len(str(visual["asset_hash"])) == 24


def test_clan_visual_hash_is_stable_for_same_content() -> None:
    first = build_clan_visual(
        "rat_swarm",
        clan_name="Рой Черного Камня",
        description="Крысы держатся у влажных плит.",
        context_tags=["undercity_seep", "d4_rift_rat_king"],
    )
    second = build_clan_visual(
        "rat_swarm",
        clan_name="Рой Черного Камня",
        description="Крысы держатся у влажных плит.",
        context_tags=["d4_rift_rat_king", "undercity_seep"],
    )

    assert first["asset_hash"] == second["asset_hash"]
    assert first["storage_key"] == second["storage_key"]
    assert first["generated_image_url"] == second["generated_image_url"]


def test_member_visual_hash_ignores_season_metadata_outside_payload() -> None:
    first = build_member_visual(
        "wolf_pack",
        variant_key="ash_runner",
        role="minion",
        member_name="Пепельный бегун",
        appearance="Худой волк с серой шерстью.",
    )
    second = build_member_visual(
        "wolf_pack",
        variant_key="ash_runner",
        role="minion",
        member_name="Пепельный бегун",
        appearance="Худой волк с серой шерстью.",
    )

    first["season_key"] = "season_001"
    second["season_key"] = "season_002"

    assert first["asset_hash"] == second["asset_hash"]
    assert first["asset_payload"] == second["asset_payload"]
    assert first["asset_payload"]["style_version"] == 4


def test_generated_visual_urls_are_versioned_for_browser_cache_busting() -> None:
    visual = {
        "image_url": "/static/generated-assets/monsters/generated/members/rat.webp",
        "generated_image_url": "/static/generated-assets/monsters/generated/members/rat.webp",
        "placeholder_image_url": "/static/images/monsters/families/rat_swarm.svg",
        "asset_hash": "rat-image-bytes",
    }

    assert version_generated_asset_url(str(visual["image_url"]), visual) == (
        "/static/generated-assets/monsters/generated/members/rat.webp?v=rat-image-bytes"
    )
    assert version_visual_image_urls(visual)["placeholder_image_url"] == (
        "/static/images/monsters/families/rat_swarm.svg"
    )


def test_pending_visual_uses_previous_hash_for_previous_image_url() -> None:
    visual = {
        "image_url": "/static/generated-assets/monsters/generated/members/rat.webp",
        "previous_image_url": "/static/generated-assets/monsters/generated/members/rat.webp",
        "asset_hash": "next-prompt-hash",
        "previous_asset_hash": "previous-image-bytes",
    }

    assert version_visual_image_urls(visual)["image_url"] == (
        "/static/generated-assets/monsters/generated/members/rat.webp?v=previous-image-bytes"
    )


def test_clan_visual_prompt_uses_roster_and_family_subject_contract() -> None:
    visual = build_clan_visual(
        "goblin_tribe",
        clan_name="Племя Сломанных Ключей",
        description="Гоблины роются в мастерских руинах.",
        context_tags=["collapsed_workshop"],
        member_roster=[
            {
                "variant_key": "goblin_sapper",
                "role": "minion",
                "name": "Подрывник",
                "appearance": "Маленький гоблин с сумкой взрывчатки.",
            }
        ],
    )

    prompt = build_monster_visual_prompt(visual["asset_payload"])

    assert "Goblins only" in prompt
    assert "Do not render human bandit leaders" in prompt
    assert "member_roster entries as the canonical subjects" in prompt
    assert "Подрывник" in prompt


def test_member_visual_prompt_requires_one_subject_without_group_composition() -> None:
    visual = build_member_visual(
        "wolf_pack",
        variant_key="ash_runner",
        role="minion",
        member_name="Пепельный бегун",
        appearance="Худой волк с серой шерстью.",
    )

    prompt = build_monster_visual_prompt(visual["asset_payload"])

    assert "exactly one individual" in prompt
    assert "one subject only" in prompt
    assert "Do not render a pack" in prompt
    assert "group portrait" not in prompt
    assert "A lean wolf pack" not in prompt
    assert "wolf_pack" not in prompt
    assert "readable or pseudo-readable symbols" in prompt
