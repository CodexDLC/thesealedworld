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

_MACING_TAGS = ["weapon", "macing", "skill_macing", "heavy", "melee"]


WEAPON_MACING_FEINTS_TECHNICAL = {
    "macing_heavy_line": FeintTechnicalDTO(
        feint_id="macing_heavy_line",
        cost=FeintCostDTO(tactics={"hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_MACING_TAGS, "hit", "accuracy", "damage"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 1.08),
            pipeline_mutation("damage_mult", 1.08),
        ],
    ),
    "macing_armor_crush": FeintTechnicalDTO(
        feint_id="macing_armor_crush",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_MACING_TAGS, "hit", "crit", "armor_crush"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("boost_flat_armor_penetration"),
            pipeline_mutation("flat_armor_penetration_bonus_pct", 0.35),
        ],
    ),
    "macing_skullbreaker": FeintTechnicalDTO(
        feint_id="macing_skullbreaker",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_MACING_TAGS, "hit", "crit", "stun", "high_cost"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.25,
                tags=["macing", "skullbreaker"],
            )
        ],
        effects=[{"id": "stun", "target_actor": "target", "conditions": {"is_crit": True}}],
    ),
    "macing_break_swing": FeintTechnicalDTO(
        feint_id="macing_break_swing",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_MACING_TAGS, "hit", "parry", "damage_reduction"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="parry_mult",
                value_override=0.15,
                tags=["macing", "break_swing"],
            )
        ],
        effects=[{"id": "debuff_2h_damage_halved", "target_actor": "target"}],
    ),
    "macing_break_stance": FeintTechnicalDTO(
        feint_id="macing_break_stance",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_MACING_TAGS, "hit", "parry", "anti_parry", "high_cost"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="parry_mult",
                value_override=0.25,
                tags=["macing", "break_stance"],
            )
        ],
        pipeline_mutations=[
            pipeline_mutation("target_parry_mult", 0.65),
            pipeline_mutation("damage_mult", 1.10),
        ],
    ),
    "macing_guard_cracker": FeintTechnicalDTO(
        feint_id="macing_guard_cracker",
        cost=FeintCostDTO(tactics={"hit": 5, "crit": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_MACING_TAGS, "hit", "crit", "ignore_block", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("ignore_block"),
            pipeline_mutation("accuracy_mult", 1.05),
        ],
    ),
}

_MACING_TEXTS = {
    "macing_heavy_line": (
        "Тяжелая линия",
        "Продавить удар",
        "Оружейный финт тяжелого оружия: следующий удар немного точнее и сильнее.",
        "выводя тяжелое оружие на силовую линию",
        "и продавливает защиту тяжелым ударом",
        "и вкладывает вес в сокрушительный крит",
    ),
    "macing_armor_crush": (
        "Смятие брони",
        "Смять броню",
        "Оружейный финт тяжелого оружия: следующий удар сильнее подавляет плоскую броню.",
        "направляя удар в жесткую часть защиты",
        "и сминает броню цели",
        "и пробивает защиту мощным критом",
    ),
    "macing_skullbreaker": (
        "Череполом",
        "Оглушить критом",
        "Оружейный финт тяжелого оружия: повышает шанс крита; критический удар оглушает цель.",
        "поднимая оружие для оглушающего пролома",
        "и встряхивает цель тяжелым попаданием",
        "и оглушает цель сокрушительным критом",
    ),
    "macing_break_swing": (
        "Сбить размах",
        "Ослабить удар",
        "Оружейный финт тяжелого оружия: усиливает ваше парирование и при попадании режет следующий урон цели.",
        "встречая удар тяжелым перехватом",
        "и сбивает размах цели",
        "и ломает силовую линию цели",
    ),
    "macing_break_stance": (
        "Разбить стойку",
        "Сломать парирование",
        "Оружейный финт тяжелого оружия: усиливает ваше парирование и снижает парирование цели.",
        "вклиниваясь тяжелым оружием в стойку цели",
        "и разбивает защитную стойку",
        "и продавливает стойку критическим ударом",
    ),
    "macing_guard_cracker": (
        "Пролом защиты",
        "Пробить блок",
        "Оружейный финт тяжелого оружия: следующий удар обходит блок щитом.",
        "разгоняя оружие для пролома защиты",
        "и пробивает блок цели",
        "и проламывает защиту критическим ударом",
    ),
}


def _macing_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _MACING_TEXTS[feint_id]
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
            miss=["но тяжелое оружие уходит мимо"],
            dodge=["но {target} успевает уйти с линии удара"],
            parry=["но {target} отводит удар"],
            block=["но {target} принимает удар на защиту"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но тяжелое оружие уходит мимо"],
            dodge=["но {target} вырывается из-под удара"],
            parry=["но {target} сбивает траекторию удара"],
            block=["но удар гаснет о защиту {target}"],
        ),
    )


WEAPON_MACING_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_macing_description(feint_id),
    )
    for feint_id, technical in WEAPON_MACING_FEINTS_TECHNICAL.items()
}
