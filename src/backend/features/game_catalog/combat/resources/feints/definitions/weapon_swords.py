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

_SWORD_TAGS = ["weapon", "swords", "skill_swords", "melee", "soft_modifier"]


WEAPON_SWORD_FEINTS_TECHNICAL = {
    "sword_measured_line": FeintTechnicalDTO(
        feint_id="sword_measured_line",
        cost=FeintCostDTO(tactics={"hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_SWORD_TAGS, "hit", "accuracy"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 1.12)],
    ),
    "sword_blade_bind": FeintTechnicalDTO(
        feint_id="sword_blade_bind",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_SWORD_TAGS, "hit", "parry", "anti_parry"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("target_parry_mult", 0.85)],
    ),
    "sword_hard_bind": FeintTechnicalDTO(
        feint_id="sword_hard_bind",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_SWORD_TAGS, "hit", "parry", "anti_parry", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("target_parry_mult", 0.65),
            pipeline_mutation("accuracy_mult", 1.05),
        ],
    ),
    "sword_low_angle": FeintTechnicalDTO(
        feint_id="sword_low_angle",
        cost=FeintCostDTO(tactics={"hit": 3, "dodge": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_SWORD_TAGS, "hit", "dodge", "anti_evasion"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("target_evasion_mult", 0.85)],
    ),
    "sword_cut_angle": FeintTechnicalDTO(
        feint_id="sword_cut_angle",
        cost=FeintCostDTO(tactics={"hit": 3, "dodge": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_SWORD_TAGS, "hit", "dodge", "anti_evasion", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("target_evasion_mult", 0.65),
            pipeline_mutation("accuracy_mult", 1.05),
        ],
    ),
    "sword_open_line": FeintTechnicalDTO(
        feint_id="sword_open_line",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_SWORD_TAGS, "hit", "crit", "crit_chance"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.15,
                tags=["swords", "crit_window"],
            )
        ],
    ),
    "sword_clean_path": FeintTechnicalDTO(
        feint_id="sword_clean_path",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_SWORD_TAGS, "hit", "crit", "crit_chance", "high_cost"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.30,
                tags=["swords", "crit_window"],
            )
        ],
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 1.05)],
    ),
    "sword_cross_arc": FeintTechnicalDTO(
        feint_id="sword_cross_arc",
        cost=FeintCostDTO(tactics={"hit": 4, "dodge": 1}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        secondary_damage_mult=0.65,
        applicability_tags=[*_SWORD_TAGS, "hit", "dodge", "damage", "multi_target"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 0.95)],
    ),
    "sword_full_circle": FeintTechnicalDTO(
        feint_id="sword_full_circle",
        cost=FeintCostDTO(tactics={"hit": 5, "dodge": 3, "crit": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.40,
        applicability_tags=[*_SWORD_TAGS, "hit", "dodge", "crit", "damage", "multi_target", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 0.85)],
    ),
    "sword_low_angle_advanced": FeintTechnicalDTO(
        feint_id="sword_low_angle_advanced",
        cost=FeintCostDTO(tactics={"hit": 3, "dodge": 2, "tempo": 1}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_SWORD_TAGS, "hit", "dodge", "tempo", "anti_evasion", "punish"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("target_evasion_mult", 0.85)],
        effects=[{"id": "debuff_accuracy", "target_actor": "target"}],
    ),
    "sword_clean_path_advanced": FeintTechnicalDTO(
        feint_id="sword_clean_path_advanced",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 5, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_SWORD_TAGS, "hit", "crit", "tempo", "crit_chance", "punish", "high_cost"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.30,
                tags=["swords", "crit_window"],
            )
        ],
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 1.05)],
        effects=[{"id": "debuff_accuracy", "target_actor": "target"}],
    ),
    "sword_full_circle_advanced": FeintTechnicalDTO(
        feint_id="sword_full_circle_advanced",
        cost=FeintCostDTO(tactics={"hit": 5, "dodge": 3, "crit": 2, "tempo": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.40,
        applicability_tags=[
            *_SWORD_TAGS,
            "hit",
            "dodge",
            "crit",
            "tempo",
            "damage",
            "multi_target",
            "punish",
            "high_cost",
        ],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 0.85)],
        effects=[{"id": "debuff_accuracy", "target_actor": "target"}],
    ),
}

_SWORD_TEXTS = {
    "sword_measured_line": (
        "Выверенная линия",
        "выверяя линию клинка провести точный удар",
        "Оружейный финт меча: следующий удар получает повышенную точность.",
        "выверяя линию клинка",
        "и проводит точный удар по линии",
        "и попадает чистой траекторией",
    ),
    "sword_blade_bind": (
        "Связать клинок",
        "давя на клинок противника снизить ему парирование",
        "Оружейный финт меча: следующий удар снижает шанс парирования цели.",
        "давя на клинок противника",
        "и мешает цели удобно парировать",
        "и раскрывает защитную линию",
    ),
    "sword_hard_bind": (
        "Жесткая связка",
        "жестко связывая клинок сильно снизить парирование",
        "Оружейный финт меча: следующий удар сильнее снижает шанс парирования цели и немного точнее.",
        "жестко связывая защиту",
        "и проводит удар через связанную линию",
        "и пробивает ритм парирования",
    ),
    "sword_low_angle": (
        "Нижний угол",
        "переводя клинок в нижний угол срезать уворот цели",
        "Оружейный финт меча: следующий удар снижает шанс уворота цели.",
        "переводя клинок в нижний угол",
        "и режет путь ухода цели",
        "и ловит движение на смене угла",
    ),
    "sword_cut_angle": (
        "Срезать угол",
        "срезая траекторию ухода сильно снизить уворот цели",
        "Оружейный финт меча: следующий удар сильнее снижает шанс уворота цели и немного точнее.",
        "срезая траекторию ухода",
        "и не дает цели легко выйти из линии",
        "и закрывает угол движения",
    ),
    "sword_open_line": (
        "Открытая линия",
        "ища открытую линию поднять шанс крита",
        "Оружейный финт меча: следующий удар получает повышенный шанс критического попадания.",
        "ища открытую линию",
        "и находит опасное окно атаки",
        "и почти превращает окно в критический удар",
    ),
    "sword_clean_path": (
        "Чистая траектория",
        "собирая чистую траекторию сильно поднять шанс крита",
        "Оружейный финт меча: следующий удар заметно повышает шанс крита и немного точнее.",
        "собирая чистую траекторию",
        "и ведет клинок в слабую точку",
        "и раскрывает сильное критовое окно",
    ),
    "sword_cross_arc": (
        "Крестовая дуга",
        "разворачиваясь провести крестовой дугой по трем целям",
        "Оружейный финт меча: основной размен задевает до двух дополнительных целей крестовой дугой.",
        "разворачивая клинок в крестовую дугу",
        "и рассекает соседнюю линию",
        "и пересекает строй опасной дугой",
    ),
    "sword_full_circle": (
        "Полный круг",
        "вкладываясь обрушить полный круг на весь строй",
        "Оружейный финт меча: основной размен задевает всех ближайших врагов широким кругом со сниженной точностью.",
        "разворачивая клинок в полный круг",
        "и рассекает строй на всю ширину",
        "и сметает строй сокрушительным кругом",
    ),
    "sword_low_angle_advanced": (
        "Карательный нижний угол",
        "наказывая промах противника срезать уворот и сбить точность",
        "Карательный финт меча: тратит темп, режет уворот цели и сбивает ей точность.",
        "наказывая промах противника нижним углом",
        "и режет уворот и сбивает точность цели",
        "и сбивает точность цели после среза угла",
    ),
    "sword_clean_path_advanced": (
        "Карательная чистая траектория",
        "наказывая промах противника собрать критовое окно и сбить точность",
        "Карательный финт меча: тратит темп, повышает шанс крита и сбивает точность цели.",
        "наказывая промах противника чистой траекторией",
        "и собирает критовое окно и сбивает точность цели",
        "и сбивает точность цели после критической траектории",
    ),
    "sword_full_circle_advanced": (
        "Карательный полный круг",
        "наказывая весь строй разрубить кругом и сбить точность всем",
        "Карательный финт меча: тратит темп, основной размен задевает всех ближайших врагов и сбивает им точность.",
        "наказывая весь строй сокрушительным кругом",
        "и рассекает строй и сбивает точность всем",
        "и сбивает точность всему строю сокрушительным кругом",
    ),
}


def _sword_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _SWORD_TEXTS[feint_id]
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
            miss=["но линия проходит мимо"],
            dodge=["но {target} уходит из-под клинка"],
            parry=["но {target} отводит меч"],
            block=["но {target} принимает удар на защиту"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но линия проходит мимо"],
            dodge=["но {target} уходит из-под клинка"],
            parry=["но {target} сбивает клинок движением"],
            block=["но удар гаснет о защиту {target}"],
        ),
    )


WEAPON_SWORD_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_sword_description(feint_id),
    )
    for feint_id, technical in WEAPON_SWORD_FEINTS_TECHNICAL.items()
}
