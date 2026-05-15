from src.backend.features.game_catalog.combat.resources.text_templates.compiler import (
    COMBAT_TEXT_CATALOG_VERSION,
    build_combat_text_catalog,
    compile_template_recipe,
)
from src.backend.features.game_catalog.combat.resources.text_templates.fragments import load_combat_text_phrases

__all__ = [
    "COMBAT_TEXT_CATALOG_VERSION",
    "build_combat_text_catalog",
    "compile_template_recipe",
    "load_combat_text_phrases",
]
