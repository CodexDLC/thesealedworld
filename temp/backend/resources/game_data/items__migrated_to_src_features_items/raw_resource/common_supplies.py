"""
ОБЩИЕ РЕСУРСЫ ДЛЯ РЕМЕСЛА (Crafting Supplies)
==============================================
Расходные материалы, которые не имеют тиров и используются в различных рецептах.
Ключом в словаре является ID ресурса.
"""

COMMON_SUPPLIES_DB = {
    "supplies": {
        "res_charcoal": {
            "id": "res_charcoal",
            "name_ru": "Древесный уголь",
            "base_price": 2,
            "narrative_description": "Простое топливо для кузнечной печи. Создается из дерева.",
        },
        "res_coal": {
            "id": "res_coal",
            "name_ru": "Каменный уголь",
            "base_price": 5,
            "narrative_description": "Более эффективное топливо, дающее сильный жар. Добывается в шахтах.",
        },
        "res_pine_resin": {
            "id": "res_pine_resin",
            "name_ru": "Сосновая смола",
            "base_price": 3,
            "narrative_description": "Липкая смола, используется для создания клея и пропитки дерева.",
        },
        "res_animal_bones": {
            "id": "res_animal_bones",
            "name_ru": "Кости животных",
            "base_price": 1,
            "narrative_description": "Можно переработать в костный клей или костяную муку.",
        },
        "res_limestone_flux": {
            "id": "res_limestone_flux",
            "name_ru": "Известняковый флюс",
            "base_price": 4,
            "narrative_description": "Порошок, который помогает очищать металл от примесей при плавке.",
        },
        "res_mineral_oil": {
            "id": "res_mineral_oil",
            "name_ru": "Минеральное масло",
            "base_price": 10,
            "narrative_description": "Используется для закалки клинков и смазки механизмов.",
        },
        "res_crude_thread": {
            "id": "res_crude_thread",
            "name_ru": "Грубая нить",
            "base_price": 2,
            "narrative_description": "Простая нить для сшивания кожи и ткани.",
        },
    }
}
