from pathlib import Path


GAME_CATALOG_JS = Path("src/frontend/static/js/core/catalog.js")
GAME_BUNDLE_JS = Path("src/frontend/static/js/game.js")


def test_game_catalog_cache_exposes_combat_text_templates() -> None:
    catalog_js = GAME_CATALOG_JS.read_text(encoding="utf-8")

    assert "getCombatTextTemplate(templateKey)" in catalog_js
    assert "this.memory?.combat_text?.templates?.[templateKey] || null" in catalog_js
    assert "getCombatTextResource(resourceType, resourceId)" in catalog_js
    assert "effect: 'effects'" in catalog_js
    assert "ability: 'abilities'" in catalog_js
    assert "const bucket = buckets[resourceType] || resourceType" in catalog_js
    assert "this.memory?.combat_text?.resources?.[bucket]?.[resourceId] || null" in catalog_js


def test_game_catalog_cache_renders_combat_text_templates_without_html() -> None:
    catalog_js = GAME_CATALOG_JS.read_text(encoding="utf-8")
    bundle_js = GAME_BUNDLE_JS.read_text(encoding="utf-8")

    for source in (catalog_js, bundle_js):
        assert "renderCombatText(templateKey, variables = {})" in source
        assert "return this.renderTemplate(entry.template, variables)" in source
        assert "renderTemplate(template, variables = {})" in source
        assert "String(template || '').replace(/\\{([a-zA-Z_][a-zA-Z0-9_]*)\\}/g" in source
        assert "if (value === undefined || value === null) return match" in source
        assert "return String(value)" in source
