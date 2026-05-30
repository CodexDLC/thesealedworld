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

_POLEARM_TAGS = ["weapon", "polearms", "skill_polearms", "control", "melee"]


WEAPON_POLEARM_FEINTS_TECHNICAL = {
    "polearm_long_line": FeintTechnicalDTO(
        feint_id="polearm_long_line",
        cost=FeintCostDTO(tactics={"hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_POLEARM_TAGS, "hit", "accuracy", "anti_evasion"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 1.10),
            pipeline_mutation("target_evasion_mult", 0.90),
        ],
    ),
    "polearm_hook_step": FeintTechnicalDTO(
        feint_id="polearm_hook_step",
        cost=FeintCostDTO(tactics={"hit": 3, "dodge": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_POLEARM_TAGS, "hit", "dodge", "trip", "debuff_evasion"],
        purchase_group="weapon",
        effects=[{"id": "debuff_evasion", "target_actor": "target"}],
    ),
    "polearm_leg_sweep": FeintTechnicalDTO(
        feint_id="polearm_leg_sweep",
        cost=FeintCostDTO(tactics={"hit": 3, "dodge": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_POLEARM_TAGS, "hit", "dodge", "trip", "knockdown", "high_cost"],
        purchase_group="weapon",
        effects=[{"id": "knockdown", "target_actor": "target"}],
    ),
    "polearm_guard_intercept": FeintTechnicalDTO(
        feint_id="polearm_guard_intercept",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_POLEARM_TAGS, "hit", "parry", "intercept", "debuff_accuracy"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="parry_mult",
                value_override=0.20,
                tags=["polearms", "intercept"],
            )
        ],
        effects=[{"id": "debuff_accuracy", "target_actor": "target"}],
    ),
    "polearm_stunning_intercept": FeintTechnicalDTO(
        feint_id="polearm_stunning_intercept",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_POLEARM_TAGS, "hit", "parry", "intercept", "stun", "high_cost"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="parry_mult",
                value_override=0.30,
                tags=["polearms", "intercept"],
            )
        ],
        effects=[{"id": "stun", "target_actor": "target"}],
    ),
    "polearm_pinning_point": FeintTechnicalDTO(
        feint_id="polearm_pinning_point",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_POLEARM_TAGS, "hit", "crit", "control_chance", "anti_evasion"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="control_chance_add",
                value_override=0.15,
                tags=["polearms", "control_window"],
            )
        ],
        pipeline_mutations=[pipeline_mutation("target_evasion_mult", 0.80)],
    ),
    "polearm_locked_distance": FeintTechnicalDTO(
        feint_id="polearm_locked_distance",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_POLEARM_TAGS, "hit", "crit", "control_chance", "knockdown", "high_cost"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="control_chance_add",
                value_override=0.30,
                tags=["polearms", "control_window"],
            )
        ],
        pipeline_mutations=[
            pipeline_mutation("target_evasion_mult", 0.70),
            pipeline_mutation("target_parry_mult", 0.80),
        ],
        effects=[{"id": "knockdown", "target_actor": "target"}],
    ),
    "polearm_line_cleave": FeintTechnicalDTO(
        feint_id="polearm_line_cleave",
        cost=FeintCostDTO(tactics={"hit": 4, "parry": 1}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        secondary_damage_mult=0.75,
        applicability_tags=[*_POLEARM_TAGS, "hit", "parry", "damage", "multi_target"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 0.95)],
    ),
}

_POLEARM_TEXTS = {
    "polearm_long_line": (
        "Длинная линия",
        "Удержать дистанцию",
        "Оружейный финт древкового: следующий удар точнее и сложнее уходит в уворот.",
        "удерживая длинную линию древка",
        "и достает цель с дистанции",
        "и ловит движение на конце древка",
    ),
    "polearm_hook_step": (
        "Зацепить шаг",
        "Ослабить уворот",
        "Оружейный финт древкового: при попадании снижает уклонение цели.",
        "цепляя шаг противника крюком древка",
        "и сбивает работу ног цели",
        "и ломает движение противника",
    ),
    "polearm_leg_sweep": (
        "Подсечка древком",
        "Сбить с ног",
        "Оружейный финт древкового: при попадании сбивает цель с ног.",
        "ведя древко в подсечку",
        "и валит цель с ног",
        "и жестко сбивает равновесие",
    ),
    "polearm_guard_intercept": (
        "Перехват древком",
        "Сбить точность",
        "Оружейный финт древкового: усиливает ваше парирование и при попадании снижает точность цели.",
        "ставя древко на перехват",
        "и сбивает прицел цели",
        "и оставляет древко на защитной линии",
    ),
    "polearm_stunning_intercept": (
        "Оглушающий перехват",
        "Оглушить",
        "Оружейный финт древкового: усиливает ваше парирование и при попадании оглушает цель.",
        "перехватывая вход жестким концом древка",
        "и оглушает цель ударом древка",
        "и срывает вход тяжелым перехватом",
    ),
    "polearm_pinning_point": (
        "Прижать острием",
        "Открыть контроль",
        "Оружейный финт древкового: повышает шанс физического контроля и режет уворот цели.",
        "прижимая цель острием",
        "и не дает цели свободно сместиться",
        "и держит опасное окно контроля",
    ),
    "polearm_locked_distance": (
        "Запертая дистанция",
        "Контроль и сбивание",
        "Оружейный финт древкового: повышает шанс контроля, режет защитные реакции и при попадании сбивает с ног.",
        "запирая дистанцию древком",
        "и закрывает цель в зоне контроля",
        "и валит цель в запертой дистанции",
    ),
    "polearm_line_cleave": (
        "Срез строя",
        "Ударить по трем целям",
        "Оружейный финт древкового: основной размен задевает до двух дополнительных целей на 75% урона.",
        "срезая строй длинной дугой древка",
        "и задевает соседние цели",
        "и прорезает линию противников",
    ),
}


def _polearm_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _POLEARM_TEXTS[feint_id]
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
            miss=["но древко проходит мимо"],
            dodge=["но {target} выходит из линии древка"],
            parry=["но {target} отводит древко"],
            block=["но {target} принимает удар на защиту"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но древко проходит мимо"],
            dodge=["но {target} выходит из линии древка"],
            parry=["но {target} сбивает древко движением"],
            block=["но удар гаснет о защиту {target}"],
        ),
    )


WEAPON_POLEARM_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_polearm_description(feint_id),
    )
    for feint_id, technical in WEAPON_POLEARM_FEINTS_TECHNICAL.items()
}
