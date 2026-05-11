from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import pipeline_mutation
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.feints.schemas import (
    FeintCatalogEntryDTO,
    FeintCostDTO,
    FeintTechnicalDTO,
)

WEAPON_FEINTS_TECHNICAL = {
    "piercing_thrust": FeintTechnicalDTO(
        feint_id="piercing_thrust",
        cost=FeintCostDTO(tactics={"hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        pipeline_mutations=[pipeline_mutation("enable_pierce")],
    ),
    "shield_bash": FeintTechnicalDTO(
        feint_id="shield_bash",
        cost=FeintCostDTO(tactics={"block": 2}),
        target=TargetType.SINGLE_ENEMY,
        effects=[{"id": "stun"}],
    ),
    "cleave": FeintTechnicalDTO(
        feint_id="cleave",
        cost=FeintCostDTO(tactics={"hit": 2, "crit": 1}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        modifier_applications=[
            ModifierApplicationDTO(modifier_id="damage_mult", value_override=-0.3),
        ],
    ),
    "pommel_strike": FeintTechnicalDTO(
        feint_id="pommel_strike",
        cost=FeintCostDTO(tactics={"tempo": 1, "hit": 1}),
        target=TargetType.SINGLE_ENEMY,
        effects=[{"id": "stun"}],
        modifier_applications=[
            ModifierApplicationDTO(modifier_id="damage_mult", value_override=-0.4),
        ],
    ),
    "hamstring_cut": FeintTechnicalDTO(
        feint_id="hamstring_cut",
        cost=FeintCostDTO(tactics={"hit": 1, "dodge": 1}),
        target=TargetType.SINGLE_ENEMY,
        effects=[{"id": "dot_bleed"}],
        modifier_applications=[
            ModifierApplicationDTO(modifier_id="damage_mult", value_override=-0.2),
        ],
    ),
    "polearm_trip": FeintTechnicalDTO(
        feint_id="polearm_trip",
        cost=FeintCostDTO(tactics={"tempo": 1, "dodge": 1}),
        target=TargetType.SINGLE_ENEMY,
        modifier_applications=[
            ModifierApplicationDTO(modifier_id="evasion_mult", target_actor="target", value_override=-0.5),
        ],
    ),
    "guard_breaker": FeintTechnicalDTO(
        feint_id="guard_breaker",
        cost=FeintCostDTO(tactics={"block": 1, "hit": 1}),
        target=TargetType.SINGLE_ENEMY,
        modifier_applications=[
            ModifierApplicationDTO(modifier_id="block_mult", target_actor="target", value_override=-0.5),
        ],
    ),
    "aimed_shot": FeintTechnicalDTO(
        feint_id="aimed_shot",
        cost=FeintCostDTO(tactics={"hit": 2, "tempo": 1}),
        target=TargetType.SINGLE_ENEMY,
        modifier_applications=[
            ModifierApplicationDTO(modifier_id="accuracy_add", value_override=0.2),
            ModifierApplicationDTO(modifier_id="damage_mult", value_override=-0.1),
        ],
    ),
    "close_grapple": FeintTechnicalDTO(
        feint_id="close_grapple",
        cost=FeintCostDTO(tactics={"tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        modifier_applications=[
            ModifierApplicationDTO(modifier_id="evasion_mult", target_actor="target", value_override=-0.5),
            ModifierApplicationDTO(modifier_id="parry_mult", target_actor="target", value_override=-0.5),
        ],
    ),
}

WEAPON_FEINTS_DESCRIPTIVE = {
    "piercing_thrust": build_combat_description(
        resource_type="feints",
        resource_id="piercing_thrust",
        icon="combat/feints/piercing_thrust.svg",
        display_name="Пронзающий выпад",
        ui_label="Уколоть в открывшуюся линию защиты",
        short_description="Игнорирует броню цели.",
        humanoid_long_description=(
            "Точный выпад в слабую линию защиты: исполнитель ищет щель в стойке, броне или движении цели."
        ),
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} смещается и ищет открытую линию для укола по {target}"],
            hit=["и находит щель в защите, нанося {damage} урона."],
            crit=["и глубоко проходит через открытую линию {target}, нанося {damage} урона."],
            miss=["но укол проходит рядом с {target}."],
            block=["но {target} закрывает линию удара."],
            parry=["но {target} отводит выпад в сторону."],
            dodge=["но {target} уходит с линии укола."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} ловит открывшийся бок {target} для точного укола"],
            hit=["и попадает в слабое место, нанося {damage} урона."],
            crit=["и глубоко поражает {target}, нанося {damage} урона."],
            miss=["но {target} дергается в сторону."],
            block=["но укол гаснет о плотную защиту {target}."],
            parry=["но {target} сбивает выпад движением корпуса."],
            dodge=["но {target} уходит с линии укола."],
        ),
    ),
    "shield_bash": build_combat_description(
        resource_type="feints",
        resource_id="shield_bash",
        icon="combat/feints/shield_bash.svg",
        display_name="Удар щитом",
        ui_label="Вдавить щитом и сорвать равновесие",
        short_description="Наносит урон и оглушает. Требует щит.",
        humanoid_long_description=(
            "Силовое движение щитом в ближней дистанции: исполнитель ломает темп цели и пытается оглушить ее."
        ),
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} вдавливает щит вперед, ломая дистанцию {target}"],
            hit=["и сбивает {target} с равновесия."],
            crit=["и оглушает {target} мощным ударом щита."],
            miss=["но {target} отступает из-под щита."],
            block=["но {target} встречает напор своей защитой."],
            parry=["но {target} уводит щит в сторону."],
            dodge=["но {target} проскальзывает мимо напора."],
            apply_effect=["{target} получает эффект {effect}."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} встречает рывок {target} ударом щита"],
            hit=["и сбивает движение {target}."],
            crit=["и резко останавливает {target} щитом."],
            miss=["но {target} уходит мимо щита."],
            block=["но удар гаснет о массу {target}."],
            parry=["но {target} сбивает щит рывком корпуса."],
            dodge=["но {target} проскакивает мимо напора."],
            apply_effect=["{target} получает эффект {effect}."],
        ),
    ),
    "cleave": build_combat_description(
        resource_type="feints",
        resource_id="cleave",
        icon="combat/feints/cleave.svg",
        display_name="Рассечение",
        ui_label="Провести широкую рубящую дугу",
        short_description="Атакует несколько целей перед собой.",
        humanoid_long_description="Широкий рубящий удар по нескольким гуманоидным противникам перед исполнителем.",
        beast_display_name="Рассечение",
        beast_short_description="Широкий удар по зверю, рассчитанный на корпус, лапы или открытую шею.",
        beast_long_description="Широкое рассечение против зверя: исполнитель ведёт оружие по дуге, чтобы поймать рывок, корпус или конечности цели.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=[
                "{source} ведет оружие широкой дугой через линию {target}",
                "{source} начинает рубящий замах по дуге в сторону {target}",
                "{source} выбирает линию рассечения перед собой",
            ],
            hit=[
                "и цепляет {target} широким ударом, нанося {damage} урона.",
                "и дуга проходит по защите {target}, нанося {damage} урона.",
                "и {target} получает рубящий удар на {damage} урона.",
            ],
            crit=[
                "и глубоко рассекает {target}, нанося {damage} урона.",
                "и тяжелая дуга раскрывает защиту {target}, нанося {damage} урона.",
                "и {target} не успевает закрыться от тяжелой дуги.",
            ],
            miss=[
                "но проводит рассечение мимо {target}.",
                "но {target} выходит из линии рассечения.",
            ],
            block=[
                "но {target} принимает рассечение на защиту.",
                "но удар вязнет в блоке {target}.",
            ],
            parry=[
                "но {target} парирует рассечение.",
                "но {target} сбивает дугу удара в сторону.",
            ],
            dodge=[
                "но {target} уходит из-под рассечения.",
                "но {target} отступает за пределы рубящей дуги.",
            ],
            apply_effect=[
                "Рассечение {source} накладывает {effect} на {target}.",
            ],
            expire_effect=[
                "{effect} после рассечения на {target} заканчивается.",
            ],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[
                "{source} ведет оружие широкой дугой против {target}",
                "{source} ловит рывок {target} и готовит рассечение",
                "{source} смещается к боку {target}, раскрывая линию рубящего удара",
            ],
            hit=[
                "и рассекает бок {target}, нанося {damage} урона.",
                "и рубящая дуга цепляет {target} на {damage} урона.",
                "и {target} попадает под рассечение.",
            ],
            crit=[
                "и глубоко рассекает открытую сторону {target}, нанося {damage} урона.",
                "и рассечение тяжело проходит по {target}, нанося {damage} урона.",
                "и {target} не успевает уйти от критической дуги.",
            ],
            miss=[
                "но {target} срывается с линии рассечения.",
                "но рубит воздух там, где только что был {target}.",
            ],
            block=[
                "но {target} принимает рассечение плотной шкурой и массой.",
                "но удар гаснет о корпус {target}.",
            ],
            parry=[
                "но {target} сбивает рассечение рывком корпуса.",
                "но {target} уводит оружие в сторону резким движением.",
            ],
            dodge=[
                "но {target} отпрыгивает от рассечения.",
                "но {target} проскальзывает ниже рубящей дуги.",
            ],
            apply_effect=[
                "Рассечение {source} оставляет {effect} на {target}.",
            ],
            expire_effect=[
                "{effect} после рассечения на {target} затухает.",
            ],
        ),
    ),
    "pommel_strike": build_combat_description(
        resource_type="feints",
        resource_id="pommel_strike",
        icon="combat/feints/pommel_strike.svg",
        display_name="Удар навершием",
        ui_label="Сблизиться и ударить навершием в лицо",
        short_description="Слабее обычного удара, но может оглушить.",
        humanoid_long_description="Короткий прием клинковым оружием: исполнитель ломает дистанцию и бьет навершием, чтобы сорвать темп цели.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} сближается и ведет навершие клинка в лицо {target}"],
            hit=["и сбивает {target} коротким ударом."],
            crit=["и жестко оглушает {target} ударом навершия."],
            miss=["но {target} отступает из ближней дистанции."],
            block=["но {target} закрывается от короткого удара."],
            parry=["но {target} перехватывает движение клинка."],
            dodge=["но {target} уходит из-под удара навершием."],
            apply_effect=["{target} получает эффект {effect}."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} сближается и бьет {target} навершием"],
            hit=["и сбивает движение {target}."],
            crit=["и резко останавливает рывок {target}."],
            miss=["но {target} отскакивает назад."],
            block=["но удар гаснет о корпус {target}."],
            parry=["но {target} сбивает движение корпусом."],
            dodge=["но {target} уходит от короткого удара."],
        ),
    ),
    "hamstring_cut": build_combat_description(
        resource_type="feints",
        resource_id="hamstring_cut",
        icon="combat/feints/hamstring_cut.svg",
        display_name="Подрез сухожилия",
        ui_label="Скользнуть ниже и подрезать ногу",
        short_description="Колюще-режущий прием, который может вызвать кровотечение.",
        humanoid_long_description="Фехтовальный прием против опоры цели: исполнитель уходит ниже линии защиты и режет по ноге или сухожилию.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} скользит ниже защиты и режет по ноге {target}"],
            hit=["и задевает сухожилие, нанося {damage} урона."],
            crit=["и глубоко подрезает опору {target}, нанося {damage} урона."],
            miss=["но {target} убирает ногу из-под реза."],
            block=["но {target} закрывает нижнюю линию."],
            parry=["но {target} сбивает клинок в сторону."],
            dodge=["но {target} отступает от подреза."],
            apply_effect=["{target} получает эффект {effect}."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} режет ниже, пытаясь поймать лапу {target}"],
            hit=["и задевает опору {target}, нанося {damage} урона."],
            crit=["и глубоко рассекает лапу {target}."],
            miss=["но {target} дергается в сторону."],
            block=["но удар гаснет о корпус {target}."],
            parry=["но {target} сбивает движение рывком."],
            dodge=["но {target} уходит от подреза."],
        ),
    ),
    "polearm_trip": build_combat_description(
        resource_type="feints",
        resource_id="polearm_trip",
        icon="combat/feints/polearm_trip.svg",
        display_name="Подсечка древком",
        ui_label="Зацепить ноги древком и сбить темп",
        short_description="Мешает цели уклоняться.",
        humanoid_long_description="Движение для копий, посохов и древкового оружия: исполнитель цепляет ноги или опору цели, мешая ей уклоняться.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} опускает древко и ищет ноги {target}"],
            hit=["и цепляет его ноги древком."],
            miss=["но {target} переступает через древко и сохраняет равновесие."],
            block=["но {target} принимает движение на щит."],
            parry=["но {target} сбивает древко в сторону."],
            dodge=["но {target} отскакивает раньше, чем древко достает до ног."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} ведет древко низко, ловя рывок {target}"],
            hit=["и сбивает шаг {target} ударом древка."],
            miss=["но {target} перескакивает через древко."],
        ),
    ),
    "guard_breaker": build_combat_description(
        resource_type="feints",
        resource_id="guard_breaker",
        icon="combat/feints/guard_breaker.svg",
        display_name="Слом защиты",
        ui_label="Вбить удар в защиту и раскрыть цель",
        short_description="Ослабляет блок цели.",
        humanoid_long_description="Дробящий прием: исполнитель бьет не по телу, а по защите, заставляя цель раскрыться.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} вбивает дробящий удар в защиту {target}"],
            hit=["и раскрывает стойку {target}."],
            crit=["и ломает защитный темп {target}, нанося {damage} урона."],
            miss=["но удар не находит защиты {target}."],
            block=["но {target} выдерживает давление блока."],
            parry=["но {target} уводит тяжелый удар в сторону."],
            dodge=["но {target} уходит до столкновения."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} бьет тяжелым оружием в корпус {target}"],
            hit=["и сбивает защитное движение {target}."],
            crit=["и тяжело продавливает {target}, нанося {damage} урона."],
            miss=["но {target} уходит с линии удара."],
            block=["но удар гаснет о массу {target}."],
            parry=["но {target} сбивает траекторию рывком."],
            dodge=["но {target} отскакивает назад."],
        ),
    ),
    "aimed_shot": build_combat_description(
        resource_type="feints",
        resource_id="aimed_shot",
        icon="combat/feints/aimed_shot.svg",
        display_name="Выверенный выстрел",
        ui_label="Выцелить открытую линию и отпустить тетиву",
        short_description="Повышает точность, слегка снижая урон.",
        humanoid_long_description="Лучник тратит темп на выцеливание, выбирая момент, когда цель раскрывается в движении.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} выцеливает открытую линию {target}"],
            hit=["и отпускает точный выстрел, нанося {damage} урона."],
            crit=["и попадает в уязвимое место {target}, нанося {damage} урона."],
            miss=["но {target} сбивает линию выстрела."],
            block=["но {target} принимает попадание на защиту."],
            parry=["но {target} сбивает снаряд в сторону."],
            dodge=["но {target} уходит с линии выстрела."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} выцеливает рывок {target}"],
            hit=["и попадает, нанося {damage} урона."],
            crit=["и точно поражает {target}, нанося {damage} урона."],
            miss=["но {target} срывается с линии выстрела."],
            dodge=["но {target} уходит с линии выстрела."],
        ),
    ),
    "close_grapple": build_combat_description(
        resource_type="feints",
        resource_id="close_grapple",
        icon="combat/feints/close_grapple.svg",
        display_name="Ближний захват",
        ui_label="Войти в клинч и прижать противника",
        short_description="Снижает защитные реакции цели.",
        humanoid_long_description="Рукопашный прием: исполнитель сближается, ломает дистанцию и мешает цели уклоняться или парировать.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} входит в клинч и давит на корпус {target}"],
            hit=["и прижимает {target}, срывая защитное движение."],
            crit=["и жестко фиксирует {target} в ближней дистанции."],
            miss=["но {target} не дает войти в захват."],
            block=["но {target} упирается и держит дистанцию."],
            parry=["но {target} сбивает вход в клинч."],
            dodge=["но {target} уходит из захвата."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} бросается в ближний захват против {target}"],
            hit=["и сбивает движение {target}."],
            crit=["и удерживает {target} в ближней дистанции."],
            miss=["но {target} вырывается из-под входа."],
            dodge=["но {target} уходит от захвата."],
        ),
    ),
}

WEAPON_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=WEAPON_FEINTS_DESCRIPTIVE[feint_id],
    )
    for feint_id, technical in WEAPON_FEINTS_TECHNICAL.items()
}
