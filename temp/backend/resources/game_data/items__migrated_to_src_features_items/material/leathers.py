"""
КОЖА (Tanned Hide)
==================
Материалы категории "leathers". Создаются из шкур.
"""

from src.backend.resources.game_data.items.schemas import MaterialDTO

LEATHERS_DB = {
    "leathers": {
        0: MaterialDTO(
            id="mat_torn_leather",
            name_ru="Лохмотья кожи",
            tier_mult=0.8,
            slots=0,
            narrative_tags=["torn", "rotten"],
        ),
        1: MaterialDTO(
            id="mat_cured_leather",
            name_ru="Дубленая кожа",
            tier_mult=1.0,
            slots=1,
            narrative_tags=["leather", "brown", "tough"],
        ),
        2: MaterialDTO(
            id="mat_thick_leather",
            name_ru="Толстая кожа",
            tier_mult=1.4,
            slots=2,
            narrative_tags=["thick", "reinforced", "beast_hide"],
        ),
        3: MaterialDTO(
            id="mat_scaled_leather",
            name_ru="Чешуйчатая кожа",
            tier_mult=2.0,
            slots=3,
            narrative_tags=["scaled", "reptilian", "hard_leather"],
        ),
        4: MaterialDTO(
            id="mat_iron_pelt",
            name_ru="Железный мех",
            tier_mult=2.8,
            slots=4,
            narrative_tags=["iron_fur", "metallic", "stiff"],
        ),
        5: MaterialDTO(
            id="mat_crystal_hide",
            name_ru="Кристальная кожа",
            tier_mult=3.8,
            slots=4,
            narrative_tags=["crystal", "glowing", "infused"],
        ),
        6: MaterialDTO(
            id="mat_void_leather",
            name_ru="Кожа Пустоты",
            tier_mult=5.2,
            slots=5,
            narrative_tags=["void", "dark", "unsettling"],
        ),
        7: MaterialDTO(
            id="mat_ancient_dragonhide",
            name_ru="Шкура древнего дракона",
            tier_mult=6.8,
            slots=6,
            narrative_tags=["dragonhide", "ancient", "legendary"],
        ),
    },
}
