from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatDescriptionDTO,
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

_TWO_HANDED_TAGS = ["tactical", "two_handed", "skill_two_handed", "weapon", "melee"]


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
    "push_stance": FeintTechnicalDTO(
        feint_id="push_stance",
        cost=FeintCostDTO(tactics={"hit": 1, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "hit", "parry", "crit_chance"],
        purchase_group="tactical",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.30,
                tags=["two_handed", "crit_window"],
            )
        ],
    ),
    "ignore_guard": FeintTechnicalDTO(
        feint_id="ignore_guard",
        cost=FeintCostDTO(tactics={"hit": 2, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "hit", "parry", "defense_bypass"],
        purchase_group="tactical",
        pipeline_mutations=[
            pipeline_mutation("ignore_evasion"),
            pipeline_mutation("ignore_parry"),
            pipeline_mutation("ignore_block"),
        ],
    ),
    "open_wound": FeintTechnicalDTO(
        feint_id="open_wound",
        cost=FeintCostDTO(tactics={"crit": 2, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "crit", "parry", "bleed"],
        purchase_group="tactical",
        effects=[
            {
                "id": "dot_bleed",
                "target_actor": "target",
                "params": {"power": 0.5},
            }
        ],
    ),
    "heavy_swing": FeintTechnicalDTO(
        feint_id="heavy_swing",
        cost=FeintCostDTO(tactics={"hit": 2, "parry": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "hit", "parry", "forced_crit", "weapon_trigger"],
        purchase_group="tactical",
        pipeline_mutations=[pipeline_mutation("force.crit")],
    ),
    "hidden_strength": FeintTechnicalDTO(
        feint_id="hidden_strength",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "hit", "parry", "forced_crit", "no_weapon_trigger", "damage"],
        purchase_group="tactical",
        pipeline_mutations=[
            pipeline_mutation("force.crit"),
            pipeline_mutation("crit_damage_boost"),
            pipeline_mutation("suppress_crit_triggers"),
        ],
    ),
    "lucky_break": FeintTechnicalDTO(
        feint_id="lucky_break",
        cost=FeintCostDTO(tactics={"crit": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_TAGS, "crit", "forced_crit", "weapon_trigger", "damage"],
        purchase_group="tactical",
        pipeline_mutations=[
            pipeline_mutation("force.crit"),
            pipeline_mutation("crit_damage_boost"),
        ],
    ),
}

_TWO_HANDED_TEXTS = {
    "crushing_pressure": (
        "Давящая стойка",
        "Сбить размах противника",
        "Двуручный финт: при попадании снижает следующий исходящий урон цели вдвое.",
        "давя весом оружия на линию атаки",
        "и сбивает размах противника",
        "и ломает темп цели тяжелым попаданием",
    ),
    "steel_line": (
        "Стальная линия",
        "Купить следующее парирование",
        "Двуручный финт: следующая атака по вам будет парирована.",
        "возвращая оружие в стальную линию",
        "и ставит оружие на встречную защиту",
        "и жестко закрывает линию парирования",
    ),
    "blade_return": (
        "Возврат клинка",
        "Повысить следующее парирование",
        "Двуручный финт: следующая входящая атака проходит против усиленного парирования.",
        "возвращая клинок после давления",
        "и усиливает линию будущего парирования",
        "и собирает оружие в точный возврат",
    ),
    "hard_intercept": (
        "Жесткий перехват",
        "Парировать и сбить размах",
        "Двуручный финт: следующая атака парируется и снижает следующий исходящий урон противника.",
        "оставляя оружие для жесткого перехвата",
        "и готовит встречный сбив",
        "и закрывает дистанцию для перехвата",
    ),
    "answering_stance": (
        "Ответная стойка",
        "Парировать и контратаковать",
        "Двуручный финт: следующая атака парируется и вызывает контратаку.",
        "собирая ответную стойку",
        "и удерживает оружие для ответа",
        "и открывает встречный удар",
    ),
    "closed_distance": (
        "Закрытая дистанция",
        "Парировать дорогим ответом",
        "Двуручный финт: следующая атака парируется и вызывает жесткую контратаку.",
        "сжимая дистанцию вокруг тяжелого оружия",
        "и готовит закрытый ответ",
        "и удерживает опасную встречу",
    ),
    "hidden_agility": (
        "Скрытая ловкость",
        "Уйти и ответить",
        "Двуручный финт: следующая атака уходит в уворот и вызывает контратаку.",
        "пряча движение за весом оружия",
        "и сохраняет скрытую ловкость",
        "и готовит резкий уход с ответом",
    ),
    "push_stance": (
        "Продавить стойку",
        "Открыть критовое окно",
        "Двуручный финт: следующий удар получает повышенный шанс крита.",
        "продавливая стойку цели",
        "и открывает критовое окно",
        "и находит слабую точку в защите",
    ),
    "ignore_guard": (
        "Игнорирование",
        "Провести удар мимо защиты",
        "Двуручный финт: следующий удар игнорирует уворот, парирование и блок.",
        "выбирая линию вне привычной защиты",
        "и проходит мимо защитной реакции",
        "и ломает защитный ритм цели",
    ),
    "open_wound": (
        "Открытая рана",
        "Открыть кровотечение",
        "Двуручный финт: успешный удар накладывает кровотечение.",
        "готовя режущую линию",
        "и открывает кровоточащую рану",
        "и глубоко раскрывает рану",
    ),
    "heavy_swing": (
        "Тяжелый замах",
        "Гарантировать крит с триггером",
        "Двуручный финт: следующий удар становится критическим и запускает оружейный крит-триггер.",
        "поднимая оружие в тяжелый замах",
        "и обрушивает критический удар",
        "и проводит тяжелый критический размен",
    ),
    "hidden_strength": (
        "Скрытая сила",
        "Крит без оружейного триггера",
        "Двуручный финт: следующий удар критический, без оружейного триггера, но с x2 уроном.",
        "собирая силу без лишнего раскрытия",
        "и бьет скрытой силой",
        "и вкладывает весь вес в чистый урон",
    ),
    "lucky_break": (
        "Слепая удача",
        "Крит с триггером и x2 уроном",
        "Двуручный финт: следующий удар критический, с оружейным триггером и x2 уроном.",
        "рискуя всем ради одного окна",
        "и ловит удачный критический момент",
        "и раскрывает удар полностью",
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
