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
        applicability_tags=[*_MACING_TAGS, "hit", "crit", "stun", "anti_archer", "high_cost"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.25,
                tags=["macing", "skullbreaker"],
            )
        ],
        effects=[
            {"id": "stun", "target_actor": "target", "conditions": {"is_crit": True}},
            {"id": "force_ranged_close", "target_actor": "target", "conditions": {"is_crit": True}},
        ],
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
    "macing_shock_sweep": FeintTechnicalDTO(
        feint_id="macing_shock_sweep",
        cost=FeintCostDTO(tactics={"hit": 5, "parry": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        secondary_damage_mult=0.65,
        applicability_tags=[*_MACING_TAGS, "hit", "parry", "damage", "anti_parry", "multi_target", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.90),
            pipeline_mutation("target_parry_mult", 0.85),
            pipeline_mutation("target_block_mult", 0.85),
        ],
    ),
    "macing_earthshatter": FeintTechnicalDTO(
        feint_id="macing_earthshatter",
        cost=FeintCostDTO(tactics={"hit": 5, "parry": 3, "crit": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.40,
        applicability_tags=[*_MACING_TAGS, "hit", "parry", "crit", "damage", "multi_target", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.85),
            pipeline_mutation("target_block_mult", 0.80),
        ],
    ),
    "macing_skullbreaker_advanced": FeintTechnicalDTO(
        feint_id="macing_skullbreaker_advanced",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 5, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[
            *_MACING_TAGS,
            "hit",
            "crit",
            "tempo",
            "stun",
            "control",
            "anti_archer",
            "high_cost",
        ],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.25,
                tags=["macing", "skullbreaker"],
            )
        ],
        effects=[
            {"id": "stun", "target_actor": "target", "conditions": {"is_crit": True}},
            {"id": "knockdown", "target_actor": "target", "conditions": {"is_crit": True}},
            {"id": "force_ranged_close", "target_actor": "target", "conditions": {"is_crit": True}},
        ],
    ),
    "macing_break_stance_advanced": FeintTechnicalDTO(
        feint_id="macing_break_stance_advanced",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 5, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[
            *_MACING_TAGS,
            "hit",
            "parry",
            "tempo",
            "anti_parry",
            "control",
            "anti_archer",
            "high_cost",
        ],
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
        effects=[
            {"id": "concussed_no_feints", "target_actor": "target"},
            {"id": "force_ranged_close", "target_actor": "target"},
        ],
    ),
    "macing_earthshatter_advanced": FeintTechnicalDTO(
        feint_id="macing_earthshatter_advanced",
        cost=FeintCostDTO(tactics={"hit": 5, "parry": 3, "crit": 2, "tempo": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.40,
        applicability_tags=[
            *_MACING_TAGS,
            "hit",
            "parry",
            "crit",
            "tempo",
            "damage",
            "multi_target",
            "control",
            "anti_archer",
            "high_cost",
        ],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.85),
            pipeline_mutation("target_block_mult", 0.80),
        ],
        effects=[
            {"id": "concussed_no_feints", "target_actor": "target"},
            {"id": "force_ranged_close", "target_actor": "target"},
        ],
    ),
}

_MACING_TEXTS = {
    "macing_heavy_line": (
        "Тяжелая линия",
        "выводя тяжелое оружие на силовую линию продавить удар",
        "Оружейный финт тяжелого оружия: следующий удар немного точнее и сильнее.",
        "выводя тяжелое оружие на силовую линию",
        "и продавливает защиту тяжелым ударом",
        "и вкладывает вес в сокрушительный крит",
    ),
    "macing_armor_crush": (
        "Смятие брони",
        "направляя удар в жесткую часть защиты смять броню",
        "Оружейный финт тяжелого оружия: следующий удар сильнее подавляет броню.",
        "направляя удар в жесткую часть защиты",
        "и сминает броню цели",
        "и пробивает защиту мощным критом",
    ),
    "macing_skullbreaker": (
        "Череполом",
        "поднимая оружие для пролома оглушить цель критом",
        "Оружейный финт тяжелого оружия: повышает шанс крита; критический удар оглушает цель.",
        "поднимая оружие для оглушающего пролома",
        "и встряхивает цель тяжелым попаданием",
        "и оглушает цель сокрушительным критом",
    ),
    "macing_break_swing": (
        "Сбить размах",
        "встречая удар тяжелым перехватом сбить размах цели",
        "Оружейный финт тяжелого оружия: усиливает ваше парирование и при попадании режет следующий урон цели.",
        "встречая удар тяжелым перехватом",
        "и сбивает размах цели",
        "и ломает силовую линию цели",
    ),
    "macing_break_stance": (
        "Разбить стойку",
        "вклиниваясь в стойку цели разбить её парирование",
        "Оружейный финт тяжелого оружия: усиливает ваше парирование и снижает парирование цели.",
        "вклиниваясь тяжелым оружием в стойку цели",
        "и разбивает защитную стойку",
        "и продавливает стойку критическим ударом",
    ),
    "macing_guard_cracker": (
        "Пролом защиты",
        "разгоняя оружие пробить блок цели",
        "Оружейный финт тяжелого оружия: следующий удар обходит блок щитом.",
        "разгоняя оружие для пролома защиты",
        "и пробивает блок цели",
        "и проламывает защиту критическим ударом",
    ),
    "macing_shock_sweep": (
        "Ударная дуга",
        "ведя тяжелое оружие дугой продавить три цели",
        "Оружейный финт тяжелого оружия: основной размен задевает до двух дополнительных целей.",
        "ведя тяжелое оружие ударной дугой",
        "и продавливает соседнюю защиту",
        "и расшатывает строй тяжелым кругом",
    ),
    "macing_earthshatter": (
        "Колеблющий землю",
        "обрушив вес обоих рук разнести строй землетрясением",
        "Оружейный финт тяжелого оружия: основной размен сотрясает всех врагов сниженной точностью и тяжелым ударом.",
        "обрушивая вес тяжелого оружия в землю",
        "и сотрясает строй колеблющим ударом",
        "и разносит строй сокрушительным колеблющим ударом",
    ),
    "macing_skullbreaker_advanced": (
        "Темповый череполом",
        "используя окно темпа обрушить крит и сбить с ног",
        "Финт тяжелого оружия: тратит темп, повышает шанс крита; критический удар оглушает и валит цель с ног, навязывая лучнику ближний бой.",
        "используя окно темпа тяжелым проломом",
        "и обрушивает крит и валит цель с ног",
        "и валит цель с ног сокрушительным критом",
    ),
    "macing_break_stance_advanced": (
        "Темповая разбитая стойка",
        "используя окно темпа разбить стойку и сорвать темп",
        "Финт тяжелого оружия: тратит темп, разбивает стойку и срывает темп цели, навязывая лучнику ближний бой.",
        "используя окно темпа тяжелым давлением",
        "и разбивает стойку и срывает темп цели",
        "и срывает темп цели сокрушительным разбиванием стойки",
    ),
    "macing_earthshatter_advanced": (
        "Темповый колеблющий",
        "используя темп сотрясти строй и сорвать темп нескольким",
        "Финт тяжелого оружия: тратит темп, тяжелая дуга задевает всех ближайших, срывает темп трем целям и навязывает лучникам ближний бой.",
        "используя темп сокрушительным землетрясением",
        "и сотрясает строй и срывает темп нескольким",
        "и срывает темп нескольким после сокрушительного землетрясения",
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
