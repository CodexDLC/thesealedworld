"""
РУДЫ (Mining)
=============
Сырье для создания материалов категории "ingots".
Добывается из жил в разломах или с тел каменных големов.
"""

from src.backend.resources.game_data.items.schemas import ResourceDTO

ORES_DB = {
    "ores": {
        0: ResourceDTO(
            id="res_rust_flakes",
            name_ru="Ржавая труха",
            base_price=1,
            narrative_description="Осыпавшаяся ржавчина. Почти бесполезна, но можно переплавить в гвозди.",
        ),
        1: ResourceDTO(
            id="res_iron_ore",
            name_ru="Железная руда",
            base_price=5,
            narrative_description="Тяжелый кусок породы с прожилками железа. Основа кузнечного дела.",
        ),
        2: ResourceDTO(
            id="res_cobalt_ore",
            name_ru="Кобальтовая руда",
            base_price=20,
            narrative_description="Синеватый камень, прочнее железа. Ценится за легкость обработки.",
        ),
        3: ResourceDTO(
            id="res_mithril_ore",
            name_ru="Мифриловая руда",
            base_price=80,
            narrative_description="Серебристый металл, легкий как перо и твердый как сталь.",
        ),
        4: ResourceDTO(
            id="res_adamantite_ore",
            name_ru="Адамантитовая руда",
            base_price=350,
            narrative_description="Зеленоватый, невероятно плотный металл. Сложно расплавить.",
        ),
        5: ResourceDTO(
            id="res_thorium_ore",
            name_ru="Ториевая руда",
            base_price=1500,
            narrative_description="Излучает слабое тепло и магическую энергию. Опасна при неправильном обращении.",
        ),
        6: ResourceDTO(
            id="res_void_metal_ore",
            name_ru="Руда Пустотного металла",
            base_price=8000,
            narrative_description="Черный металл, который не отражает свет. Кажется, он поглощает звуки вокруг.",
        ),
        7: ResourceDTO(
            id="res_star_metal_ore",
            name_ru="Звездная руда",
            base_price=50000,
            narrative_description="Метеоритное железо, упавшее с небес. Обладает свойствами, недоступными земным металлам.",
        ),
    },
}
