from src.backend.features.game_catalog.services import GameCatalogBootstrapService


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
    assert "combat_entries" in payload.catalogs
    assert "battle_axe" in payload.catalogs["items"]
    assert payload.catalogs["items"]["battle_axe"]["title"] == "Боевой топор"
    assert "skill_swords" in payload.catalogs["skills"]
    assert "strength" in payload.catalogs["attributes"]
    assert payload.catalogs["abilities"]["fireball"]["title"] == "Огненный Шар"
    assert payload.catalogs["feints"]["true_strike"]["title"] == "Верный удар"
    assert payload.catalogs["combat_entries"]["combat.feint.cleave"]["resource_id"] == "cleave"
    assert payload.catalogs["combat_entries"]["combat.feint.cleave"]["taxonomy_variants"]["beast"]["event_texts"]["hit"]
    assert payload.catalogs["effects"]["dot_burn"]["title"] == "Ожог"
    assert payload.catalogs["gifts"]["gift_true_fire"]["title"] == "Истинное Пламя"
    assert payload.manifest.catalogs["items"].startswith("sha256:")
    assert payload.manifest.catalogs["skills"].startswith("sha256:")
    assert payload.manifest.catalogs["abilities"].startswith("sha256:")
    assert payload.manifest.catalogs["combat_entries"].startswith("sha256:")
    assert "stat_weights" not in payload.catalogs["skills"]["skill_swords"]
