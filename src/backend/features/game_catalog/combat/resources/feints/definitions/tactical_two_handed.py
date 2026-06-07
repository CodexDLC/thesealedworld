from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatDescriptionDTO,
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.feints.schemas import (
    FeintCatalogEntryDTO,
    FeintCostDTO,
    FeintTechnicalDTO,
)

_TWO_HANDED_TAGS = ["tactical", "two_handed", "skill_two_handed", "melee"]


TACTICAL_TWO_HANDED_FEINTS_TECHNICAL = {
    "crushing_pressure": FeintTechnicalDTO(
        feint_id="crushing_pressure",
        cost=FeintCostDTO(tactics={"hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "hit", "debuff", "damage_reduction"],
        purchase_group="tactical",
        effects=[{"id": "debuff_2h_damage_halved", "target_actor": "target"}],
    ),
    "steel_line": FeintTechnicalDTO(
        feint_id="steel_line",
        cost=FeintCostDTO(tactics={"crit": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "crit", "preparation", "parry"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_2h_steel_line", "target_actor": "source"}],
    ),
    "blade_return": FeintTechnicalDTO(
        feint_id="blade_return",
        cost=FeintCostDTO(tactics={"hit": 2, "crit": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "hit", "crit", "preparation", "parry_boost"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_2h_blade_return", "target_actor": "source"}],
    ),
    "hard_intercept": FeintTechnicalDTO(
        feint_id="hard_intercept",
        cost=FeintCostDTO(tactics={"hit": 1, "crit": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "hit", "crit", "preparation", "parry", "debuff"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_2h_hard_intercept", "target_actor": "source"}],
    ),
    "answering_stance": FeintTechnicalDTO(
        feint_id="answering_stance",
        cost=FeintCostDTO(tactics={"hit": 2, "crit": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "hit", "crit", "preparation", "parry", "counter"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_2h_answering_stance", "target_actor": "source"}],
    ),
    "closed_distance": FeintTechnicalDTO(
        feint_id="closed_distance",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 4}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "hit", "crit", "preparation", "parry", "counter", "high_cost"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_2h_closed_distance", "target_actor": "source"}],
    ),
    "hidden_agility": FeintTechnicalDTO(
        feint_id="hidden_agility",
        cost=FeintCostDTO(tactics={"hit": 1, "crit": 3, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "hit", "crit", "parry", "preparation", "dodge", "counter"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_2h_hidden_agility", "target_actor": "source"}],
    ),
    "2h_brace_to_blade": FeintTechnicalDTO(
        feint_id="2h_brace_to_blade",
        cost=FeintCostDTO(tactics={"dodge": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "dodge", "converter", "parry_gain"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_2h_brace_to_blade", "target_actor": "source"}],
    ),
    "2h_blade_to_break": FeintTechnicalDTO(
        feint_id="2h_blade_to_break",
        cost=FeintCostDTO(tactics={"parry": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "parry", "converter", "crit_gain"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_2h_blade_to_break", "target_actor": "source"}],
    ),
    "2h_break_to_step": FeintTechnicalDTO(
        feint_id="2h_break_to_step",
        cost=FeintCostDTO(tactics={"crit": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "crit", "converter", "dodge_gain"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_2h_break_to_step", "target_actor": "source"}],
    ),
    "2h_press_to_parry": FeintTechnicalDTO(
        feint_id="2h_press_to_parry",
        cost=FeintCostDTO(tactics={"pressure": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "pressure", "converter", "parry_gain"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_2h_press_to_parry", "target_actor": "source"}],
    ),
    "2h_blood_to_crit": FeintTechnicalDTO(
        feint_id="2h_blood_to_crit",
        cost=FeintCostDTO(tactics={"blood": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "blood", "converter", "crit_window"],
        purchase_group="tactical",
        preparation_effects=[{"id": "prep_2h_blood_to_crit", "target_actor": "source"}],
    ),
    "2h_perfect_riposte": FeintTechnicalDTO(
        feint_id="2h_perfect_riposte",
        cost=FeintCostDTO(tactics={"parry": 7}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "parry", "heal", "counter", "high_cost"],
        purchase_group="tactical",
        preparation_effects=[
            {
                "id": "prep_perfect_riposte",
                "target_actor": "source",
                "params": {"heal_max_hp_ratio": 0.12, "heal_min": 6},
            },
        ],
    ),
}

_TWO_HANDED_TEXTS = {
    "crushing_pressure": (
        "Давящая стойка",
        "давя весом оружия сбить размах противника",
        "Двуручный финт: при попадании снижает следующий исходящий урон цели вдвое.",
        "давя весом оружия на линию атаки",
        "и сбивает размах противника",
        "и ломает темп цели тяжелым попаданием",
    ),
    "steel_line": (
        "Стальная линия",
        "возвращая клинок в линию подготовить парирование",
        "Двуручный финт: следующая атака по вам будет парирована.",
        "возвращая оружие в стальную линию",
        "и ставит оружие на встречную защиту",
        "и жестко закрывает линию парирования",
    ),
    "blade_return": (
        "Возврат клинка",
        "возвращая клинок поднять следующее парирование",
        "Двуручный финт: следующая входящая атака проходит против усиленного парирования.",
        "возвращая клинок после давления",
        "и усиливает линию будущего парирования",
        "и собирает оружие в точный возврат",
    ),
    "hard_intercept": (
        "Жесткий перехват",
        "оставляя оружие на линии перехватить и сбить размах",
        "Двуручный финт: следующая атака парируется и снижает следующий исходящий урон противника.",
        "оставляя оружие для жесткого перехвата",
        "и готовит встречный сбив",
        "и закрывает дистанцию для перехвата",
    ),
    "answering_stance": (
        "Ответная стойка",
        "собирая оружие в стойку парировать и контратаковать",
        "Двуручный финт: следующая атака парируется и вызывает контратаку.",
        "собирая ответную стойку",
        "и удерживает оружие для ответа",
        "и открывает встречный удар",
    ),
    "closed_distance": (
        "Закрытая дистанция",
        "сжимая дистанцию парировать жестким ответом",
        "Двуручный финт: следующая атака парируется и вызывает жесткую контратаку.",
        "сжимая дистанцию вокруг тяжелого оружия",
        "и готовит закрытый ответ",
        "и удерживает опасную встречу",
    ),
    "hidden_agility": (
        "Скрытая ловкость",
        "пряча движение уйти с линии и ответить",
        "Двуручный финт: следующая атака уходит в уворот и вызывает контратаку.",
        "пряча движение за весом оружия",
        "и сохраняет скрытую ловкость",
        "и готовит резкий уход с ответом",
    ),
    "2h_brace_to_blade": (
        "Перевод стойки",
        "уворачиваясь поставить оружие для парирования",
        "Двуручный финт-конвертер: тратит уворот и усиливает следующее парирование x2.",
        "уводя корпус и сразу собирая клинок в стойку",
        "и закрепляет переход в защитную линию",
        "и точно ловит момент для встречной линии",
    ),
    "2h_blade_to_break": (
        "Окно после защиты",
        "отводя удар выждать щель для следующего",
        "Двуручный финт-конвертер: тратит парирование и делает следующую точную атаку критом.",
        "отводя клинок противника по дуге",
        "и удерживает щель для следующего удара",
        "и точно раскрывает критовое окно",
    ),
    "2h_break_to_step": (
        "Уход после крита",
        "закрепив крит уйти с линии",
        "Двуручный финт-конвертер: тратит крит и делает следующую входящую атаку уворотом.",
        "закрепляя крит широким шагом",
        "и уходит с линии после тяжелого удара",
        "и оставляет линию пустой за собой",
    ),
    "2h_press_to_parry": (
        "Давление в защиту",
        "надавив корпусом перехватить линию обороны",
        "Двуручный финт-конвертер: тратит давление и усиливает следующее парирование x3.",
        "надавливая корпусом на линию противника",
        "и сразу переводит давление в защитную стойку",
        "и закрывает линию обороны точным движением",
    ),
    "2h_blood_to_crit": (
        "Боль в удар",
        "выдержав боль обрушить следующий удар",
        "Двуручный финт-конвертер: тратит кровь и поднимает шанс крита следующего удара.",
        "выдыхая накопленную боль",
        "и закрепляет тяжелую линию следующего удара",
        "и собирает боль в опасное критовое окно",
    ),
    "2h_perfect_riposte": (
        "Совершенный рипост",
        "сохраняя оружие для рипоста парировать восстановиться и ответить",
        "Двуручный финт: следующее успешное парирование восстанавливает HP и вызывает контратаку.",
        "сохраняя оружие для рипоста",
        "и держит линию ответа после контакта",
        "и открывает опасный рипост",
    ),
}


def _two_handed_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _TWO_HANDED_TEXTS[feint_id]
    return build_combat_description(
        resource_type="feints",
        resource_id=feint_id,
        icon=f"combat/feints/{feint_id}.svg",
        display_name=display_name,
        ui_label=ui_label,
        short_description=short,
        humanoid_long_description=short,
        humanoid_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но тяжелая линия не находит цели"],
            dodge=["но {target} уходит из-под веса оружия"],
            parry=["но {target} отводит тяжелую атаку"],
            block=["но {target} принимает удар на защиту"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но тяжелая линия не находит цели"],
            dodge=["но {target} уходит из-под веса оружия"],
            parry=["но {target} сбивает атаку движением"],
            block=["но удар гаснет о защиту {target}"],
        ),
    )


TACTICAL_TWO_HANDED_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_two_handed_description(feint_id),
    )
    for feint_id, technical in TACTICAL_TWO_HANDED_FEINTS_TECHNICAL.items()
}
