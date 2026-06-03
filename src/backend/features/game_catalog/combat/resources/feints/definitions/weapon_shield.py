from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatDescriptionDTO,
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import pipeline_mutation
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.feints.schemas import (
    FeintCatalogEntryDTO,
    FeintCostDTO,
    FeintTechnicalDTO,
)

_WEAPON_SHIELD_TAGS = ["weapon", "shield", "skill_shield_mastery", "shield_bash", "melee"]


WEAPON_SHIELD_FEINTS_TECHNICAL = {
    "concussion": FeintTechnicalDTO(
        feint_id="concussion",
        cost=FeintCostDTO(tactics={"block": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_WEAPON_SHIELD_TAGS, "hit", "control", "anti_archer"],
        purchase_group="weapon",
        effects=[
            {"id": "concussed_no_feints", "target_actor": "target"},
            {"id": "force_ranged_close", "target_actor": "target"},
        ],
    ),
    "shield_line_bash": FeintTechnicalDTO(
        feint_id="shield_line_bash",
        cost=FeintCostDTO(tactics={"hit": 3, "block": 3}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        secondary_damage_mult=0.45,
        applicability_tags=[*_WEAPON_SHIELD_TAGS, "hit", "control", "multi_target", "anti_archer"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 0.90)],
        effects=[
            {"id": "debuff_accuracy", "target_actor": "target"},
            {"id": "force_ranged_close", "target_actor": "target"},
        ],
    ),
    "bloody_rebuke": FeintTechnicalDTO(
        feint_id="bloody_rebuke",
        cost=FeintCostDTO(tactics={"blood": 1, "hit": 2, "block": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_WEAPON_SHIELD_TAGS, "hit", "blood", "damage"],
        purchase_group="weapon",
        effects=[
            {"id": "shield_blood_damage", "target_actor": "target", "params": {"damage": 10}},
        ],
    ),
    "blood_wall_crash": FeintTechnicalDTO(
        feint_id="blood_wall_crash",
        cost=FeintCostDTO(tactics={"blood": 1, "hit": 3, "block": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_WEAPON_SHIELD_TAGS, "hit", "blood", "damage", "control", "anti_archer"],
        purchase_group="weapon",
        effects=[
            {"id": "shield_blood_damage", "target_actor": "target", "params": {"damage": 12}},
            {"id": "knockdown", "target_actor": "target"},
            {"id": "force_ranged_close", "target_actor": "target"},
        ],
    ),
    "red_line_bash": FeintTechnicalDTO(
        feint_id="red_line_bash",
        cost=FeintCostDTO(tactics={"blood": 1, "hit": 4, "block": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        secondary_damage_mult=0.50,
        applicability_tags=[*_WEAPON_SHIELD_TAGS, "hit", "blood", "damage", "multi_target"],
        purchase_group="weapon",
        effects=[
            {"id": "shield_blood_damage", "target_actor": "target", "params": {"damage": 8}},
        ],
    ),
    "shield_aegis_break": FeintTechnicalDTO(
        feint_id="shield_aegis_break",
        cost=FeintCostDTO(tactics={"hit": 5, "block": 3, "parry": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.40,
        applicability_tags=[*_WEAPON_SHIELD_TAGS, "hit", "block", "parry", "damage", "multi_target", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 0.85)],
        effects=[
            {"id": "debuff_accuracy", "target_actor": "target"},
        ],
    ),
    "concussion_advanced": FeintTechnicalDTO(
        feint_id="concussion_advanced",
        cost=FeintCostDTO(tactics={"block": 3, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_WEAPON_SHIELD_TAGS, "hit", "tempo", "control", "anti_archer", "punish"],
        purchase_group="weapon",
        effects=[
            {"id": "concussed_no_feints", "target_actor": "target"},
            {"id": "force_ranged_close", "target_actor": "target"},
            {"id": "debuff_accuracy", "target_actor": "target", "params": {"duration": 2}},
        ],
    ),
    "shield_line_bash_advanced": FeintTechnicalDTO(
        feint_id="shield_line_bash_advanced",
        cost=FeintCostDTO(tactics={"hit": 3, "block": 3, "tempo": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        secondary_damage_mult=0.45,
        applicability_tags=[*_WEAPON_SHIELD_TAGS, "hit", "tempo", "control", "multi_target", "anti_archer", "punish"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 0.90)],
        effects=[
            {"id": "debuff_accuracy", "target_actor": "target", "params": {"duration": 2}},
            {"id": "force_ranged_close", "target_actor": "target"},
        ],
    ),
    "shield_aegis_break_advanced": FeintTechnicalDTO(
        feint_id="shield_aegis_break_advanced",
        cost=FeintCostDTO(tactics={"hit": 5, "block": 3, "parry": 2, "tempo": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.40,
        applicability_tags=[
            *_WEAPON_SHIELD_TAGS,
            "hit",
            "block",
            "parry",
            "tempo",
            "damage",
            "multi_target",
            "control",
            "punish",
            "high_cost",
        ],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 0.85)],
        effects=[
            {"id": "debuff_accuracy", "target_actor": "target", "params": {"duration": 2}},
        ],
    ),
}

_WEAPON_SHIELD_TEXTS = {
    "concussion": (
        "Контузия",
        "вынеся щит в корпус оглушить цель",
        "Оружейный финт щита: удар щитом наносит урон и срывает концентрацию цели, а лучника принуждает к ближнему бою.",
        "вынося щит в короткий удар",
        "и попадает щитом в корпус",
        "и жестко срывает концентрацию цели",
    ),
    "shield_line_bash": (
        "Щитовой проход",
        "вынеся щит в проход сбить три цели",
        "Оружейный финт щита: основной удар щитом задевает до двух дополнительных целей, сбивая их точность и навязывая ближний бой лучникам.",
        "вынося щит в проход по линии",
        "и сбивает строй щитом",
        "и срывает прицел нескольким целям",
    ),
    "bloody_rebuke": (
        "Кровавый упрек",
        "вложив пережитую боль в щит ответить ударом",
        "Оружейный финт щита: тратит кровь и добавляет ответный урон к успешному удару.",
        "вкладывая пережитую боль в удар щитом",
        "и возвращает накопленную боль щитом",
        "и отвечает кровавым щитовым ударом",
    ),
    "blood_wall_crash": (
        "Кровавый пролом",
        "разогнав щит через боль проломить стойку и сбить с ног",
        "Оружейный финт щита: тратит кровь, добавляет урон, сбивает цель с ног и принуждает лучника к ближнему бою.",
        "разгоняя щит через боль",
        "и проламывает стойку щитом",
        "и вбивает цель в землю кровавым напором",
    ),
    "red_line_bash": (
        "Красная линия",
        "ведя щит по красной линии задеть три цели",
        "Оружейный финт щита: тратит кровь и задевает щитовым ударом до трех целей.",
        "ведя щит по красной линии",
        "и разносит давление по строю",
        "и возвращает боль сразу нескольким целям",
    ),
    "shield_aegis_break": (
        "Пролом эгиды",
        "разгоняясь протаранить строй щитом",
        "Оружейный финт щита: основной размен задевает всех ближайших врагов сниженной точностью, разносит их щитом и сбивает точность каждому.",
        "разгоняясь в широкий таран щитом",
        "и проламывает строй на всю ширину",
        "и сметает строй сокрушительным щитом",
    ),
    "concussion_advanced": (
        "Карательная контузия",
        "наказывая промах противника срезать темп и сбить точность",
        "Карательный финт щита: тратит темп, срывает темп цели, сбивает её точность на два размена и навязывает лучнику ближний бой.",
        "наказывая промах противника жестким контактом",
        "и срывает темп цели и сбивает её точность",
        "и срывает темп цели сокрушительным щитом",
    ),
    "shield_line_bash_advanced": (
        "Карательный щитовой проход",
        "наказывая строй врагов протаранить три цели и сбить им точность",
        "Карательный финт щита: тратит темп, основной удар задевает три цели, сбивает им точность на два размена и навязывает лучнику ближний бой.",
        "наказывая строй врагов щитовым проходом",
        "и протаранивает строй и сбивает точность всем",
        "и сбивает точность всему фронту сокрушительным проходом",
    ),
    "shield_aegis_break_advanced": (
        "Карательный пролом эгиды",
        "наказывая весь строй протаранить его щитом и сбить точность всем",
        "Карательный финт щита: тратит темп, основной размен задевает всех ближайших врагов и сбивает им точность на два размена.",
        "наказывая весь строй сокрушительным щитом",
        "и протаранивает строй и сбивает точность всем",
        "и сбивает точность всему строю сокрушительным щитом",
    ),
}


def _shield_weapon_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _WEAPON_SHIELD_TEXTS[feint_id]
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
            miss=["но щит не достает цели"],
            dodge=["но {target} уходит из-под щита"],
            parry=["но {target} отводит щит в сторону"],
            block=["но {target} принимает удар на защиту"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но щит не достает цели"],
            dodge=["но {target} уходит из-под щита"],
            parry=["но {target} сбивает щит движением"],
            block=["но удар гаснет о защиту {target}"],
        ),
    )


WEAPON_SHIELD_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_shield_weapon_description(feint_id),
    )
    for feint_id, technical in WEAPON_SHIELD_FEINTS_TECHNICAL.items()
}
