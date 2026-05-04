"""
ВАЛЮТА И ЭКОНОМИКА
==================
Основная валюта игры, имеющая физическое воплощение и градации ценности.
"""

from src.backend.resources.game_data.items.schemas import ResourceDTO

CURRENCY_DB = {
    "currency": {
        0: ResourceDTO(
            id="currency_dust",
            name_ru="Пыль Резидуу",
            base_price=1,
            narrative_description="Мерцающий песок. Остаточная энергия Рифтов. Основа всей экономики.",
        ),
        1: ResourceDTO(
            id="currency_fragment",
            name_ru="Фрагмент Энергии",
            base_price=10,
            narrative_description="Небольшой кусочек застывшей силы. Удобен для мелких сделок.",
        ),
        2: ResourceDTO(
            id="currency_shard",
            name_ru="Стабильный Осколок",
            base_price=100,
            narrative_description="Спрессованная энергия. Стандартная валюта для торговли между игроками.",
        ),
        3: ResourceDTO(
            id="currency_crystal",
            name_ru="Сияющий Кристалл",
            base_price=1000,
            narrative_description="Крупный кристалл, пульсирующий светом. Небольшое состояние.",
        ),
        4: ResourceDTO(
            id="currency_orb",
            name_ru="Энергетическая Сфера",
            base_price=10000,
            narrative_description="Идеально гладкая сфера, в которой заключена огромная сила. Признак богатства.",
        ),
        5: ResourceDTO(
            id="currency_prism",
            name_ru="Радужная Призма",
            base_price=100000,
            narrative_description="Переливается всеми цветами радуги. Используется для самых дорогих сделок.",
        ),
        6: ResourceDTO(
            id="currency_core",
            name_ru="Ядро Чистоты",
            base_price=1000000,
            narrative_description="Идеальная форма энергии. Целое состояние в одном камне.",
        ),
        7: ResourceDTO(
            id="currency_star",
            name_ru="Искра Звезды",
            base_price=10000000,
            narrative_description="Говорят, это осколок настоящей звезды. Владеть таким - значит владеть миром.",
        ),
    },
}
