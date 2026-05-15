from src.backend.features.monsters.resources.visuals import build_clan_visual, build_member_visual, get_family_visual


def test_family_visual_exposes_content_addressed_generated_target() -> None:
    visual = get_family_visual("rat_swarm")

    assert visual["status"] == "fallback"
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
