from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.feints.schemas import (
    FeintCatalogEntryDTO,
    FeintCostDTO,
    FeintTechnicalDTO,
)

TACTICAL_FEINTS_TECHNICAL = {
    "true_strike": FeintTechnicalDTO(
        feint_id="true_strike",
        cost=FeintCostDTO(tactics={"hit": 2}),
        target=TargetType.SINGLE_ENEMY,
        triggers=["accuracy.true_strike"],
        modifier_applications=[
            ModifierApplicationDTO(modifier_id="damage_mult", value_override=-0.2),
        ],
    ),
    "power_attack": FeintTechnicalDTO(
        feint_id="power_attack",
        cost=FeintCostDTO(tactics={"crit": 1, "hit": 1}),
        target=TargetType.SINGLE_ENEMY,
        modifier_applications=[
            ModifierApplicationDTO(modifier_id="damage_mult", value_override=0.5),
            ModifierApplicationDTO(modifier_id="accuracy_add", value_override=-0.2),
        ],
    ),
    "defensive_strike": FeintTechnicalDTO(
        feint_id="defensive_strike",
        cost=FeintCostDTO(tactics={"tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        triggers=["dodge.counter_on_dodge"],
    ),
}

TACTICAL_FEINTS_DESCRIPTIVE = {
    "true_strike": build_combat_description(
        resource_type="feints",
        resource_id="true_strike",
        icon="combat/feints/true_strike.svg",
        display_name="Верный удар",
        ui_label="Выждать момент и ударить наверняка",
        short_description="Игнорирует уклонение противника, но наносит меньше урона.",
        humanoid_long_description=(
            "Осторожная атака с приоритетом на попадание: исполнитель жертвует частью силы удара, "
            "чтобы не дать цели уйти движением."
        ),
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} выжидает момент и ведет удар по открытой линии {target}"],
            hit=["и попадает, не давая {target} уйти движением."],
            crit=["и точно пробивает защиту {target}, нанося {damage} урона."],
            miss=["но {target} срывает дистанцию в последний миг."],
            block=["но {target} закрывает линию удара блоком."],
            parry=["но {target} встречает удар и отводит оружие в сторону."],
            dodge=["но {target} все же успевает выйти из линии атаки."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} ловит движение {target} и бьет наверняка"],
            hit=["и попадает по открывшейся стороне {target}."],
            crit=["и точно поражает {target}, нанося {damage} урона."],
            miss=["но {target} рвется в сторону раньше удара."],
            block=["но удар гаснет о массу и защиту {target}."],
            parry=["но {target} сбивает атаку резким движением корпуса."],
            dodge=["но {target} уходит с линии атаки."],
        ),
    ),
    "power_attack": build_combat_description(
        resource_type="feints",
        resource_id="power_attack",
        icon="combat/feints/power_attack.svg",
        display_name="Сильный удар",
        ui_label="Вложиться в тяжелый удар",
        short_description="Наносит повышенный урон, но снижает точность.",
        humanoid_long_description=(
            "Рискованный силовой удар: исполнитель раскрывается и бьет тяжелее, но цели проще сорвать атаку."
        ),
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} вкладывается в тяжелый удар по {target}"],
            hit=["и пробивает защиту, нанося {damage} урона."],
            crit=["и обрушивает удар с полной силой, нанося {damage} урона."],
            miss=["но тяжелый замах проходит мимо {target}."],
            block=["но {target} принимает удар на защиту."],
            parry=["но {target} сбивает тяжелый замах в сторону."],
            dodge=["но {target} успевает уйти из-под удара."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} вкладывает вес в тяжелый удар по {target}"],
            hit=["и попадает, нанося {damage} урона."],
            crit=["и тяжело поражает {target}, нанося {damage} урона."],
            miss=["но {target} срывается с линии удара."],
            block=["но удар гаснет о корпус {target}."],
            parry=["но {target} сбивает траекторию рывком."],
            dodge=["но {target} уходит из-под тяжелого удара."],
        ),
    ),
    "defensive_strike": build_combat_description(
        resource_type="feints",
        resource_id="defensive_strike",
        icon="combat/feints/defensive_strike.svg",
        display_name="Осторожный удар",
        ui_label="Ударить и оставить себе путь для защиты",
        short_description="Удар с подготовкой к защите. Повышает шанс контратаки при уклонении.",
        humanoid_long_description=(
            "Сдержанная атака без полного раскрытия: исполнитель проверяет защиту цели и готовит ответное движение."
        ),
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} атакует {target}, не раскрываясь полностью"],
            hit=["и задевает цель, сохраняя позицию для защиты."],
            crit=["и наказывает ошибку {target}, нанося {damage} урона."],
            miss=["но оставляет себе пространство для ответного движения."],
            block=["но {target} ставит блок, не ломая стойку {source}."],
            parry=["но {target} парирует осторожный удар."],
            dodge=["но {target} уходит от удара и рискует получить ответ."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} коротко атакует {target}, сохраняя равновесие"],
            hit=["и задевает {target}, не теряя позиции."],
            crit=["и точно ловит рывок {target}, нанося {damage} урона."],
            miss=["но не проваливается вслед за ударом."],
            block=["но удар гаснет о защиту {target}."],
            parry=["но {target} сбивает атаку движением корпуса."],
            dodge=["но {target} уходит и открывает себя для ответа."],
        ),
    ),
}

TACTICAL_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=TACTICAL_FEINTS_DESCRIPTIVE[feint_id],
    )
    for feint_id, technical in TACTICAL_FEINTS_TECHNICAL.items()
}
