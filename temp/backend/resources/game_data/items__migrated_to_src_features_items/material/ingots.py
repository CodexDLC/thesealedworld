"""
СЛИТКИ (Refined Metal)
======================
Материалы категории "ingots". Создаются из руды.
"""

from src.backend.resources.game_data.items.schemas import MaterialDTO

INGOTS_DB = {
    "ingots": {
        0: MaterialDTO(
            id="mat_scrap_metal",
            name_ru="Ржавый лом",
            tier_mult=0.8,
            slots=0,
            narrative_tags=["rusty", "junk", "old"],
        ),
        1: MaterialDTO(
            id="mat_iron_ingot",
            name_ru="Железный слиток",
            tier_mult=1.0,
            slots=1,
            narrative_tags=["iron", "heavy", "reliable"],
        ),
        2: MaterialDTO(
            id="mat_cobalt_ingot",
            name_ru="Кобальтовый слиток",
            tier_mult=1.5,
            slots=2,
            narrative_tags=["cobalt", "blueish", "hard"],
        ),
        3: MaterialDTO(
            id="mat_mithril_ingot",
            name_ru="Мифриловый слиток",
            tier_mult=2.2,
            slots=3,
            narrative_tags=["mithril", "light", "shining", "elven"],
        ),
        4: MaterialDTO(
            id="mat_adamantite_ingot",
            name_ru="Адамантитовый слиток",
            tier_mult=3.0,
            slots=4,
            narrative_tags=["adamantite", "unbreakable", "greenish"],
        ),
        5: MaterialDTO(
            id="mat_thorium_ingot",
            name_ru="Ториевый слиток",
            tier_mult=4.0,
            slots=4,
            narrative_tags=["thorium", "glowing", "radioactive"],
        ),
        6: MaterialDTO(
            id="mat_void_metal_ingot",
            name_ru="Слиток Пустотного металла",
            tier_mult=5.5,
            slots=5,
            narrative_tags=["void", "dark", "absorbing"],
        ),
        7: MaterialDTO(
            id="mat_star_metal_ingot",
            name_ru="Слиток Звездного металла",
            tier_mult=7.0,
            slots=6,
            narrative_tags=["star_metal", "celestial", "cosmic"],
        ),
    },
}
