"""
ШКУРЫ (Skinning)
================
Сырье для создания материалов категории "leathers".
"""

from src.backend.resources.game_data.items.schemas import ResourceDTO

HIDES_DB = {
    "hides": {
        0: ResourceDTO(
            id="res_torn_pelt",
            name_ru="Дырявая шкура",
            base_price=1,
            narrative_description="Шкура, испорченная паразитами и временем. Годится только на заплатки.",
        ),
        1: ResourceDTO(
            id="res_rough_hide",
            name_ru="Грубая шкура",
            base_price=4,
            narrative_description="Жесткая шкура дикого зверя. Требует хорошей обработки.",
        ),
        2: ResourceDTO(
            id="res_thick_hide",
            name_ru="Толстая шкура",
            base_price=15,
            narrative_description="Плотная кожа, способная выдержать скользящий удар.",
        ),
        3: ResourceDTO(
            id="res_scaled_hide",
            name_ru="Чешуйчатая шкура",
            base_price=60,
            narrative_description="Шкура, покрытая природной костяной броней.",
        ),
        4: ResourceDTO(
            id="res_iron_fur",
            name_ru="Железная шерсть",
            base_price=300,
            narrative_description="Шерсть настолько жесткая, что звенит при ударе.",
        ),
        5: ResourceDTO(
            id="res_crystal_carapace",
            name_ru="Кристальный панцирь",
            base_price=1500,
            narrative_description="Фрагмент хитина, проросший магическими кристаллами.",
        ),
        6: ResourceDTO(
            id="res_void_skin",
            name_ru="Кожа Пустоты",
            base_price=7500,
            narrative_description="Черная, маслянистая на ощупь кожа. Кажется, она поглощает тепло.",
        ),
        7: ResourceDTO(
            id="res_ancient_scale",
            name_ru="Древняя чешуя",
            base_price=40000,
            narrative_description="Неразрушимая пластина, снятая с существа, помнящего рождение мира.",
        ),
    },
}
