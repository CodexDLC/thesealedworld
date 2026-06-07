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

_TWO_HANDED_WEAPON_TAGS = ["weapon", "two_handed", "skill_two_handed", "melee"]


WEAPON_TWO_HANDED_FEINTS_TECHNICAL = {
    "push_stance": FeintTechnicalDTO(
        feint_id="push_stance",
        cost=FeintCostDTO(tactics={"hit": 1, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_WEAPON_TAGS, "hit", "parry", "crit_chance"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.30,
                tags=["two_handed", "crit_window"],
            )
        ],
    ),
    "two_handed_momentum_strike": FeintTechnicalDTO(
        feint_id="two_handed_momentum_strike",
        cost=FeintCostDTO(tactics={"hit": 3, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_WEAPON_TAGS, "hit", "tempo", "stun", "control", "bonus_damage"],
        purchase_group="weapon",
        hit_damage_bonus_per_tier=2,
        effects=[
            {"id": "stun", "target_actor": "target"},
        ],
    ),
    "ignore_guard": FeintTechnicalDTO(
        feint_id="ignore_guard",
        cost=FeintCostDTO(tactics={"hit": 2, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_WEAPON_TAGS, "hit", "parry", "defense_bypass"],
        purchase_group="weapon",
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
        applicability_tags=[*_TWO_HANDED_WEAPON_TAGS, "crit", "parry", "bleed"],
        purchase_group="weapon",
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
        applicability_tags=[*_TWO_HANDED_WEAPON_TAGS, "hit", "parry", "forced_crit", "weapon_trigger"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("force.crit")],
    ),
    "hidden_strength": FeintTechnicalDTO(
        feint_id="hidden_strength",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_TWO_HANDED_WEAPON_TAGS, "hit", "parry", "forced_crit", "no_weapon_trigger", "damage"],
        purchase_group="weapon",
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
        applicability_tags=[*_TWO_HANDED_WEAPON_TAGS, "crit", "forced_crit", "weapon_trigger", "damage"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("force.crit"),
            pipeline_mutation("crit_damage_boost"),
        ],
    ),
    "two_handed_whirl": FeintTechnicalDTO(
        feint_id="two_handed_whirl",
        cost=FeintCostDTO(tactics={"hit": 5, "parry": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        secondary_damage_mult=0.65,
        applicability_tags=[*_TWO_HANDED_WEAPON_TAGS, "hit", "parry", "damage", "multi_target", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.90),
            pipeline_mutation("target_parry_mult", 0.85),
            pipeline_mutation("target_block_mult", 0.85),
        ],
    ),
    "two_handed_devastation": FeintTechnicalDTO(
        feint_id="two_handed_devastation",
        cost=FeintCostDTO(tactics={"hit": 5, "parry": 3, "crit": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.45,
        applicability_tags=[*_TWO_HANDED_WEAPON_TAGS, "hit", "parry", "crit", "damage", "multi_target", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.85),
            pipeline_mutation("target_parry_mult", 0.80),
            pipeline_mutation("target_block_mult", 0.80),
        ],
    ),
    "heavy_swing_advanced": FeintTechnicalDTO(
        feint_id="heavy_swing_advanced",
        cost=FeintCostDTO(tactics={"hit": 2, "parry": 3, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[
            *_TWO_HANDED_WEAPON_TAGS,
            "hit",
            "parry",
            "tempo",
            "forced_crit",
            "weapon_trigger",
            "anti_archer",
        ],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("force.crit")],
        effects=[
            {"id": "knockdown", "target_actor": "target"},
            {"id": "force_ranged_close", "target_actor": "target"},
        ],
    ),
    "ignore_guard_advanced": FeintTechnicalDTO(
        feint_id="ignore_guard_advanced",
        cost=FeintCostDTO(tactics={"hit": 2, "parry": 2, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[
            *_TWO_HANDED_WEAPON_TAGS,
            "hit",
            "parry",
            "tempo",
            "defense_bypass",
            "control",
            "anti_archer",
        ],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("ignore_evasion"),
            pipeline_mutation("ignore_parry"),
            pipeline_mutation("ignore_block"),
        ],
        effects=[
            {"id": "concussed_no_feints", "target_actor": "target"},
            {"id": "force_ranged_close", "target_actor": "target"},
        ],
    ),
    "lucky_break_advanced": FeintTechnicalDTO(
        feint_id="lucky_break_advanced",
        cost=FeintCostDTO(tactics={"crit": 5, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[
            *_TWO_HANDED_WEAPON_TAGS,
            "crit",
            "tempo",
            "forced_crit",
            "weapon_trigger",
            "damage",
        ],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("force.crit"),
            pipeline_mutation("crit_damage_boost"),
        ],
        effects=[
            {"id": "debuff_2h_damage_halved", "target_actor": "target"},
        ],
    ),
    "two_handed_whirl_advanced": FeintTechnicalDTO(
        feint_id="two_handed_whirl_advanced",
        cost=FeintCostDTO(tactics={"hit": 5, "parry": 2, "tempo": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        secondary_damage_mult=0.65,
        applicability_tags=[
            *_TWO_HANDED_WEAPON_TAGS,
            "hit",
            "parry",
            "tempo",
            "damage",
            "multi_target",
            "high_cost",
        ],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.90),
            pipeline_mutation("target_parry_mult", 0.85),
            pipeline_mutation("target_block_mult", 0.85),
        ],
        effects=[
            {"id": "debuff_2h_damage_halved", "target_actor": "target"},
        ],
    ),
    "two_handed_devastation_advanced": FeintTechnicalDTO(
        feint_id="two_handed_devastation_advanced",
        cost=FeintCostDTO(tactics={"hit": 5, "parry": 3, "crit": 2, "tempo": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.45,
        applicability_tags=[
            *_TWO_HANDED_WEAPON_TAGS,
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
            pipeline_mutation("target_parry_mult", 0.80),
            pipeline_mutation("target_block_mult", 0.80),
        ],
        effects=[
            {"id": "knockdown", "target_actor": "target"},
            {"id": "force_ranged_close", "target_actor": "target"},
        ],
    ),
}

_TWO_HANDED_TEXTS = {
    "push_stance": (
        "Продавить стойку",
        "продавив стойку открыть критическое окно",
        "Двуручный финт: следующий удар получает повышенный шанс крита.",
        "продавливая стойку цели",
        "и открывает критовое окно",
        "и находит слабую точку в защите",
    ),
    "two_handed_momentum_strike": (
        "Удар на размахе",
        "поймав темп размаха обрушить вес оружия и оглушить цель",
        "Двуручный финт на темп: бонусный урон и оглушение цели при попадании.",
        "поймав темп размаха",
        "и оглушает цель тяжелым ударом",
        "и обрушивает разящий темповой замах",
    ),
    "ignore_guard": (
        "Игнорирование",
        "выбрав линию вне защиты провести удар мимо",
        "Двуручный финт: следующий удар игнорирует уворот, парирование и блок.",
        "выбирая линию вне привычной защиты",
        "и проходит мимо защитной реакции",
        "и ломает защитный ритм цели",
    ),
    "open_wound": (
        "Открытая рана",
        "проведя режущую линию открыть кровотечение",
        "Двуручный финт: успешный удар накладывает кровотечение.",
        "готовя режущую линию",
        "и открывает кровоточащую рану",
        "и глубоко раскрывает рану",
    ),
    "heavy_swing": (
        "Тяжелый замах",
        "подняв оружие гарантировать критический удар с триггером",
        "Двуручный финт: следующий удар становится критическим и запускает оружейный крит-триггер.",
        "поднимая оружие в тяжелый замах",
        "и обрушивает критический удар",
        "и проводит тяжелый критический размен",
    ),
    "hidden_strength": (
        "Скрытая сила",
        "собрав силу обрушить чистый критический удар",
        "Двуручный финт: следующий удар критический, без оружейного триггера, но с x2 уроном.",
        "собирая силу без лишнего раскрытия",
        "и бьет скрытой силой",
        "и вкладывает весь вес в чистый урон",
    ),
    "lucky_break": (
        "Слепая удача",
        "поймав удачу обрушить критический удар с триггером",
        "Двуручный финт: следующий удар критический, с оружейным триггером и x2 уроном.",
        "рискуя всем ради одного окна",
        "и ловит удачный критический момент",
        "и раскрывает удар полностью",
    ),
    "two_handed_whirl": (
        "Тяжелый круг",
        "ведя оружие кругом задеть три цели",
        "Двуручный финт: основной размен задевает до двух дополнительных целей.",
        "ведя оружие тяжелым кругом",
        "и продавливает соседнюю линию",
        "и разбрасывает давление по строю",
    ),
    "two_handed_devastation": (
        "Тяжелое опустошение",
        "вкладываясь обрушить тяжелую дугу на всех",
        "Двуручный финт: основной размен задевает всех ближайших врагов сниженной точностью и тяжелым ударом.",
        "вкладывая вес в широкую дугу",
        "и обрушивает тяжелое опустошение на строй",
        "и разносит строй сокрушительной дугой",
    ),
    "heavy_swing_advanced": (
        "Темповый тяжелый замах",
        "используя окно темпа обрушить тяжелый замах и сбить с ног",
        "Двуручный финт: тратит темп, критический удар сбивает цель с ног и навязывает лучнику ближний бой.",
        "используя окно темпа тяжелым весом",
        "и обрушивает крит и валит цель с ног",
        "и валит цель с ног тяжелым критом",
    ),
    "ignore_guard_advanced": (
        "Темповое игнорирование",
        "используя окно темпа пройти мимо защиты и сорвать темп",
        "Двуручный финт: тратит темп, игнорирует все защитные реакции и срывает темп цели.",
        "используя окно темпа обходом защиты",
        "и проходит мимо защиты и срывает темп",
        "и срывает темп цели обходом защиты",
    ),
    "lucky_break_advanced": (
        "Темповая удача",
        "используя окно темпа обрушить тяжелый крит и сбить размах",
        "Двуручный финт: тратит темп, критический удар наносит усиленный урон и режет следующий урон цели.",
        "используя окно темпа тяжелой удачей",
        "и обрушивает тяжелый крит и сбивает размах",
        "и сбивает размах цели после тяжелого крита",
    ),
    "two_handed_whirl_advanced": (
        "Темповый тяжелый круг",
        "используя темп обрушить круг и сбить следующий урон строю",
        "Двуручный финт: тратит темп, основной размен задевает три цели и режет их следующий урон.",
        "используя темп тяжелым кругом",
        "и обрушивает круг и сбивает следующий урон всем",
        "и сбивает следующий урон всем затронутым кругом",
    ),
    "two_handed_devastation_advanced": (
        "Темповое опустошение",
        "используя темп обрушить тяжелую дугу и сбить с ног нескольких",
        "Двуручный финт: тратит темп, тяжелая дуга задевает всех ближайших, валит затронутых и навязывает лучникам ближний бой.",
        "используя темп сокрушительной дугой",
        "и обрушивает дугу и валит затронутых",
        "и сметает строй и валит затронутых сокрушительной дугой",
    ),
}


def _two_handed_weapon_description(feint_id: str) -> CombatDescriptionDTO:
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


WEAPON_TWO_HANDED_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_two_handed_weapon_description(feint_id),
    )
    for feint_id, technical in WEAPON_TWO_HANDED_FEINTS_TECHNICAL.items()
}
