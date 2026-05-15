import uuid

from src.backend.features.game_catalog.services import GameCatalogBootstrapService
from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster


def test_game_catalog_bootstrap_contains_safe_text_catalogs():
    payload = GameCatalogBootstrapService().build_bootstrap()

    assert payload.version
    assert "items" in payload.catalogs
    assert "skills" in payload.catalogs
    assert "attributes" in payload.catalogs
    assert "abilities" in payload.catalogs
    assert "feints" in payload.catalogs
    assert "effects" in payload.catalogs
    assert "triggers" in payload.catalogs
    assert "gifts" in payload.catalogs
    assert "combat_tokens" in payload.catalogs
    assert "combat_entries" in payload.catalogs
    assert "combat_text" in payload.catalogs
    assert "monster_families" in payload.catalogs
    assert "battle_axe" in payload.catalogs["items"]
    assert payload.catalogs["items"]["battle_axe"]["title"] == "Боевой топор"
    assert "skill_swords" in payload.catalogs["skills"]
    assert "strength" in payload.catalogs["attributes"]
    assert payload.catalogs["abilities"]["fireball"]["title"] == "Огненный Шар"
    assert payload.catalogs["feints"]["true_strike"]["title"] == "Верный удар"
    assert payload.catalogs["combat_entries"]["combat.ability.fireball"]["resource_id"] == "fireball"
    assert payload.catalogs["combat_entries"]["combat.ability.fireball"]["taxonomy_variants"]["humanoid"]["event_texts"][
        "area_result"
    ]
    assert payload.catalogs["combat_entries"]["combat.gift.gift_true_fire"]["resource_id"] == "gift_true_fire"
    assert payload.catalogs["combat_entries"]["combat.item.fire_grenade"]["resource_id"] == "fire_grenade"
    assert payload.catalogs["combat_entries"]["combat.feint.cleave"]["resource_id"] == "cleave"
    assert payload.catalogs["combat_entries"]["combat.feint.cleave"]["taxonomy_variants"]["beast"]["event_texts"]["hit"]
    assert payload.catalogs["combat_text"]["templates"]
    assert payload.catalogs["combat_text"]["resources"]["abilities"]["fireball"]["template_keys"]
    assert payload.catalogs["effects"]["dot_burn"]["title"] == "Ожог"
    assert payload.catalogs["gifts"]["gift_true_fire"]["title"] == "Истинное Пламя"
    assert payload.catalogs["combat_tokens"]["tempo"]["title"] == "Темп"
    assert payload.catalogs["combat_tokens"]["parry"]["icon"] == "token-parry"
    assert payload.catalogs["monster_families"]["wolf_pack"]["variant_count"] > 0
    assert payload.catalogs["monster_families"]["wolf_pack"]["visual"]["image_url"].endswith("wolf_pack.svg")
    assert payload.catalogs["monster_families"]["wolf_pack"]["variants"][0]["role"] in {
        "minion",
        "veteran",
        "elite",
        "boss",
    }
    assert payload.manifest.catalogs["items"].startswith("sha256:")
    assert payload.manifest.catalogs["skills"].startswith("sha256:")
    assert payload.manifest.catalogs["abilities"].startswith("sha256:")
    assert payload.manifest.catalogs["combat_tokens"].startswith("sha256:")
    assert payload.manifest.catalogs["combat_entries"].startswith("sha256:")
    assert payload.manifest.catalogs["combat_text"].startswith("sha256:")
    assert payload.manifest.catalogs["monster_families"].startswith("sha256:")
    assert "stat_weights" not in payload.catalogs["skills"]["skill_swords"]


def test_game_catalog_projects_generated_monster_clans():
    clan_id = uuid.uuid4()
    clan = GeneratedClan(
        id=clan_id,
        family_id="wolf_pack",
        tier=1,
        zone_id="D4_0_0",
        context_hash="context",
        unique_hash="unique",
        raw_tags={"biome": "forest", "tags": ["cold"]},
        flavor_content={"mood": "hungry"},
        name_ru="",
        description="",
        members=[
            GeneratedMonster(
                id=uuid.uuid4(),
                clan_id=clan_id,
                variant_key="runner",
                role="minion",
                member_tier=0,
                threat_rating=12,
                name_ru="",
                description="Fast scout",
                text_content={},
                scaled_attributes={"agility": 16},
                scaled_skills={"skill_fencing": 0.2},
                items={},
                vitals={},
                ai_profile={},
                generation_meta={
                    "visual": {
                        "status": "fallback",
                        "image_url": "/static/images/monsters/families/wolf_pack.svg",
                        "storage_key": "monsters/generated/families/test.webp",
                    }
                },
            )
        ],
    )

    payload = GameCatalogBootstrapService().project_generated_monster_clans([clan])

    assert payload[0]["id"] == str(clan_id)
    assert payload[0]["family_key"] == "wolf_pack"
    assert payload[0]["family_label"] == "Ashen Wolves"
    assert payload[0]["title"] == "Ashen Wolves"
    assert payload[0]["summary"].startswith("Lean predators")
    assert payload[0]["danger"] == "Low threat"
    assert payload[0]["visual"]["image_url"] == "/static/images/monsters/families/wolf_pack.svg"
    assert payload[0]["member_count"] == 1
    assert payload[0]["members"][0]["role_label"] == "Common form"
    assert payload[0]["members"][0]["visual"]["image_url"] == "/static/images/monsters/families/wolf_pack.svg"
    assert payload[0]["members"][0]["danger"] == "Minor threat"
    assert payload[0]["members"][0]["public_stats"] == [{"label": "Agility", "value": 16}]
    assert payload[0]["members"][0]["public_skills"] == ["Fencing"]
    assert "family_id" not in payload[0]
    assert "zone_id" not in payload[0]
    assert "context_hash" not in payload[0]
    assert "unique_hash" not in payload[0]
    assert "raw_tags" not in payload[0]
    assert "variant_key" not in payload[0]["members"][0]
    assert "combat_seed" not in payload[0]["members"][0]
