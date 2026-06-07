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

_DUAL_WEAPON_TAGS = ["weapon", "dual_wield", "skill_dual_wield", "melee"]


WEAPON_DUAL_WIELD_FEINTS_TECHNICAL = {
    "open_vein": FeintTechnicalDTO(
        feint_id="open_vein",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_WEAPON_TAGS, "hit", "parry", "crit_chance"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.30,
                tags=["dual_wield", "dagger_window"],
            )
        ],
    ),
    "silent_puncture": FeintTechnicalDTO(
        feint_id="silent_puncture",
        cost=FeintCostDTO(tactics={"hit": 5, "parry": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_DUAL_WEAPON_TAGS, "hit", "parry", "forced_crit", "weapon_trigger", "damage"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("force.crit"),
            pipeline_mutation("crit_damage_boost"),
        ],
    ),
    "dual_cross_slash": FeintTechnicalDTO(
        feint_id="dual_cross_slash",
        cost=FeintCostDTO(tactics={"hit": 3, "dodge": 1}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        secondary_damage_mult=0.65,
        applicability_tags=[*_DUAL_WEAPON_TAGS, "hit", "dodge", "damage", "multi_target"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 0.95)],
    ),
    "dual_blade_whirl": FeintTechnicalDTO(
        feint_id="dual_blade_whirl",
        cost=FeintCostDTO(tactics={"hit": 5, "dodge": 3, "crit": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.40,
        applicability_tags=[
            *_DUAL_WEAPON_TAGS,
            "hit",
            "dodge",
            "crit",
            "damage",
            "multi_target",
            "offhand",
            "high_cost",
        ],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.85),
            pipeline_mutation("suppress_crit_triggers"),
        ],
    ),
    "open_vein_advanced": FeintTechnicalDTO(
        feint_id="open_vein_advanced",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 3, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[
            *_DUAL_WEAPON_TAGS,
            "hit",
            "parry",
            "tempo",
            "crit_chance",
            "control",
            "anti_archer",
        ],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.30,
                tags=["dual_wield", "dagger_window"],
            )
        ],
        effects=[
            {"id": "concussed_no_feints", "target_actor": "target", "conditions": {"is_crit": True}},
            {"id": "force_ranged_close", "target_actor": "target", "conditions": {"is_crit": True}},
        ],
    ),
    "silent_puncture_advanced": FeintTechnicalDTO(
        feint_id="silent_puncture_advanced",
        cost=FeintCostDTO(tactics={"hit": 5, "parry": 3, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[
            *_DUAL_WEAPON_TAGS,
            "hit",
            "parry",
            "tempo",
            "forced_crit",
            "weapon_trigger",
            "damage",
            "offhand_followup",
        ],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("force.crit"),
            pipeline_mutation("crit_damage_boost"),
            pipeline_mutation("chain.trigger_offhand_attack"),
        ],
    ),
    "dual_blade_whirl_advanced": FeintTechnicalDTO(
        feint_id="dual_blade_whirl_advanced",
        cost=FeintCostDTO(tactics={"hit": 5, "dodge": 3, "crit": 2, "tempo": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.40,
        applicability_tags=[
            *_DUAL_WEAPON_TAGS,
            "hit",
            "dodge",
            "crit",
            "tempo",
            "damage",
            "multi_target",
            "high_cost",
        ],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.85),
            pipeline_mutation("suppress_crit_triggers"),
        ],
        effects=[
            {"id": "debuff_accuracy", "target_actor": "target"},
        ],
    ),
}

_DUAL_WEAPON_TEXTS = {
    "open_vein": (
        "Открытая жила",
        "выискивая жилу поднять шанс крита",
        "Оружейный финт двух клинков: следующий удар получает повышенный шанс крита.",
        "выискивая тонкую линию",
        "и открывает шанс критического прокола",
        "и находит живую точку",
    ),
    "silent_puncture": (
        "Тихий прокол",
        "пряча клинок гарантировать критический прокол",
        "Оружейный финт двух клинков: следующий удар критический и наносит усиленный критический урон.",
        "пряча второй клинок",
        "и проводит тихий критический прокол",
        "и раскрывает броню точным проколом",
    ),
    "dual_cross_slash": (
        "Крестовой срез",
        "раскручиваясь пройтись двойным крестом по трем целям",
        "Оружейный финт двух клинков: основной размен задевает до двух дополнительных целей крестом клинков.",
        "разводя клинки в короткий круг",
        "и режет соседние линии",
        "и пересекает строй опасным крестом",
    ),
    "dual_blade_whirl": (
        "Вихрь двух клинков",
        "разворачивая клинки разнести строй вихрем",
        "Оружейный финт двух клинков: основной размен задевает всех ближайших врагов сниженной точностью и сильно сниженным уроном.",
        "разводя клинки в широкий вихрь",
        "и режет всех в радиусе",
        "и превращает темп в широкий вихрь",
    ),
    "open_vein_advanced": (
        "Темповая открытая жила",
        "используя окно темпа открыть жилу и сорвать темп при крите",
        "Финт двух клинков: тратит темп, повышает шанс крита; при крите срывает темп цели и навязывает лучнику ближний бой.",
        "используя окно темпа тонким проколом",
        "и открывает шанс крита и срывает темп цели",
        "и срывает темп цели критическим проколом",
    ),
    "silent_puncture_advanced": (
        "Темповый тихий прокол",
        "используя окно темпа провести тихий прокол и развернуть вторую руку следом",
        "Финт двух клинков: тратит темп, критический прокол и обязательная follow-up атака второй рукой.",
        "используя окно темпа тихим проколом",
        "и обрушивает крит и сразу заводит вторую руку",
        "и заводит вторую руку следом за критическим проколом",
    ),
    "dual_blade_whirl_advanced": (
        "Темповый вихрь клинков",
        "используя темп разнести строй вихрем и сбить им точность",
        "Финт двух клинков: тратит темп, основной размен разносит весь строй и сбивает точность всем затронутым.",
        "используя темп широким вихрем клинков",
        "и режет строй и сбивает им точность",
        "и сбивает точность всему строю вихрем клинков",
    ),
}


def _dual_weapon_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _DUAL_WEAPON_TEXTS[feint_id]
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
            miss=["но дуальная линия не находит цели"],
            dodge=["но {target} уходит из-под связки"],
            parry=["но {target} сбивает связку"],
            block=["но {target} гасит серию защитой"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но дуальная линия не находит цели"],
            dodge=["но {target} уходит из-под связки"],
            parry=["но {target} сбивает движение"],
            block=["но серия гаснет о защиту {target}"],
        ),
    )


WEAPON_DUAL_WIELD_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_dual_weapon_description(feint_id),
    )
    for feint_id, technical in WEAPON_DUAL_WIELD_FEINTS_TECHNICAL.items()
}
