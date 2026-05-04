from src.backend.features.game_catalog.skills.services import SkillCatalogService


def test_skill_catalog_loads_public_text_projection():
    catalog = SkillCatalogService()

    public_text = catalog.all_public_text()

    assert "skill_swords" in public_text
    assert public_text["skill_swords"]["title"] == "Владение мечами"
    assert public_text["skill_swords"]["description"]
    assert "stat_weights" not in public_text["skill_swords"]
