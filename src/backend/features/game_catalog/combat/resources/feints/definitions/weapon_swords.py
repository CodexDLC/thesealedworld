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
    "sword_blade_whirl": FeintTechnicalDTO(
        feint_id="sword_blade_whirl",
        cost=FeintCostDTO(tactics={"hit": 5, "dodge": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=5,
        secondary_damage_mult=0.50,
        applicability_tags=[*_SWORD_TAGS, "hit", "dodge", "damage", "multi_target", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 0.95)],
    ),
}

_SWORD_TEXTS = {
    "sword_measured_line": (
        "Выверенная линия",
        "Повысить точность",
        "Оружейный финт меча: следующий удар получает повышенную точность.",
        "выверяя линию клинка",
        "и проводит точный удар по линии",
        "и попадает чистой траекторией",
    ),
    "sword_blade_bind": (
        "Связать клинок",
        "Снизить парирование",
        "Оружейный финт меча: следующий удар снижает шанс парирования цели.",
        "давя на клинок противника",
        "и мешает цели удобно парировать",
        "и раскрывает защитную линию",
    ),
    "sword_hard_bind": (
        "Жесткая связка",
        "Сильно снизить парирование",
        "Оружейный финт меча: следующий удар сильнее снижает шанс парирования цели и немного точнее.",
        "жестко связывая защиту",
        "и проводит удар через связанную линию",
        "и пробивает ритм парирования",
    ),
    "sword_low_angle": (
        "Нижний угол",
        "Снизить уворот",
        "Оружейный финт меча: следующий удар снижает шанс уворота цели.",
        "переводя клинок в нижний угол",
        "и режет путь ухода цели",
        "и ловит движение на смене угла",
    ),
    "sword_cut_angle": (
        "Срезать угол",
        "Сильно снизить уворот",
        "Оружейный финт меча: следующий удар сильнее снижает шанс уворота цели и немного точнее.",
        "срезая траекторию ухода",
        "и не дает цели легко выйти из линии",
        "и закрывает угол движения",
    ),
    "sword_open_line": (
        "Открытая линия",
        "Повысить шанс крита",
        "Оружейный финт меча: следующий удар получает повышенный шанс критического попадания.",
        "ища открытую линию",
        "и находит опасное окно атаки",
        "и почти превращает окно в критический удар",
    ),
    "sword_clean_path": (
        "Чистая траектория",
        "Сильно повысить шанс крита",
        "Оружейный финт меча: следующий удар заметно повышает шанс крита и немного точнее.",
        "собирая чистую траекторию",
        "и ведет клинок в слабую точку",
        "и раскрывает сильное критовое окно",
    ),
    "sword_blade_whirl": (
        "Вихрь клинка",
        "Задеть несколько целей",
        "Оружейный финт меча: основной размен задевает до пяти врагов отголосками половинного урона.",
        "разворачивая клинок в широкий круг",
        "и рассекает линию рядом с целью",
        "и превращает размен в широкий вихрь",
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
