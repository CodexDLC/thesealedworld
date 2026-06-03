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

_FENCING_TAGS = ["weapon", "fencing", "skill_fencing", "piercing", "melee"]


WEAPON_FENCING_FEINTS_TECHNICAL = {
    "fencing_precise_prick": FeintTechnicalDTO(
        feint_id="fencing_precise_prick",
        cost=FeintCostDTO(tactics={"hit": 3}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_FENCING_TAGS, "hit", "accuracy"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 1.12)],
    ),
    "fencing_corner_entry": FeintTechnicalDTO(
        feint_id="fencing_corner_entry",
        cost=FeintCostDTO(tactics={"hit": 3, "dodge": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_FENCING_TAGS, "hit", "dodge", "crit_chance"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.20,
                tags=["fencing", "dodge_to_crit"],
            )
        ],
    ),
    "fencing_hidden_entry": FeintTechnicalDTO(
        feint_id="fencing_hidden_entry",
        cost=FeintCostDTO(tactics={"hit": 3, "dodge": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_FENCING_TAGS, "hit", "dodge", "forced_crit", "weapon_trigger", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("force.crit"),
            pipeline_mutation("target_evasion_mult", 0.75),
        ],
    ),
    "fencing_gap_probe": FeintTechnicalDTO(
        feint_id="fencing_gap_probe",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_FENCING_TAGS, "hit", "crit", "armor_gap", "parry_boost"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="parry_mult",
                value_override=0.15,
                tags=["fencing", "crit_to_parry"],
            )
        ],
        pipeline_mutations=[
            pipeline_mutation("roll_flat_armor_ignore"),
            pipeline_mutation("flat_armor_ignore_chance_bonus", 0.25),
        ],
    ),
    "fencing_needle_gap": FeintTechnicalDTO(
        feint_id="fencing_needle_gap",
        cost=FeintCostDTO(tactics={"hit": 3, "crit": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_FENCING_TAGS, "hit", "crit", "armor_bypass", "parry_boost", "high_cost"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="parry_mult",
                value_override=0.30,
                tags=["fencing", "crit_to_parry"],
            )
        ],
        pipeline_mutations=[
            pipeline_mutation("ignore_flat_armor"),
            pipeline_mutation("accuracy_mult", 1.05),
        ],
    ),
    "fencing_slip_guard": FeintTechnicalDTO(
        feint_id="fencing_slip_guard",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_FENCING_TAGS, "hit", "parry", "evasion_boost"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="evasion_mult",
                value_override=0.15,
                tags=["fencing", "parry_to_dodge"],
            )
        ],
    ),
    "fencing_inside_line": FeintTechnicalDTO(
        feint_id="fencing_inside_line",
        cost=FeintCostDTO(tactics={"hit": 3, "parry": 5}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_FENCING_TAGS, "hit", "parry", "ignore_parry", "evasion_boost", "high_cost"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="evasion_mult",
                value_override=0.30,
                tags=["fencing", "parry_to_dodge"],
            )
        ],
        pipeline_mutations=[
            pipeline_mutation("ignore_parry"),
            pipeline_mutation("accuracy_mult", 1.05),
        ],
    ),
    "fencing_line_flurry": FeintTechnicalDTO(
        feint_id="fencing_line_flurry",
        cost=FeintCostDTO(tactics={"hit": 4, "dodge": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        secondary_damage_mult=0.55,
        applicability_tags=[*_FENCING_TAGS, "hit", "dodge", "damage", "multi_target"],
        purchase_group="weapon",
        pipeline_mutations=[pipeline_mutation("accuracy_mult", 1.02)],
    ),
    "fencing_storm_lattice": FeintTechnicalDTO(
        feint_id="fencing_storm_lattice",
        cost=FeintCostDTO(tactics={"hit": 5, "dodge": 3, "crit": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.40,
        applicability_tags=[*_FENCING_TAGS, "hit", "dodge", "crit", "damage", "multi_target", "high_cost"],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.85),
            pipeline_mutation("target_parry_mult", 0.85),
        ],
    ),
    "fencing_corner_entry_advanced": FeintTechnicalDTO(
        feint_id="fencing_corner_entry_advanced",
        cost=FeintCostDTO(tactics={"hit": 3, "dodge": 2, "tempo": 1}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[*_FENCING_TAGS, "hit", "dodge", "tempo", "crit_chance", "anti_parry", "punish"],
        purchase_group="weapon",
        modifier_applications=[
            ModifierApplicationDTO(
                modifier_id="crit_chance_add",
                value_override=0.20,
                tags=["fencing", "dodge_to_crit"],
            )
        ],
        pipeline_mutations=[pipeline_mutation("target_parry_mult", 0.85)],
    ),
    "fencing_hidden_entry_advanced": FeintTechnicalDTO(
        feint_id="fencing_hidden_entry_advanced",
        cost=FeintCostDTO(tactics={"hit": 3, "dodge": 5, "tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        applicability_tags=[
            *_FENCING_TAGS,
            "hit",
            "dodge",
            "tempo",
            "forced_crit",
            "weapon_trigger",
            "anti_parry",
            "punish",
            "high_cost",
        ],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("force.crit"),
            pipeline_mutation("target_evasion_mult", 0.75),
            pipeline_mutation("target_parry_mult", 0.70),
        ],
    ),
    "fencing_storm_lattice_advanced": FeintTechnicalDTO(
        feint_id="fencing_storm_lattice_advanced",
        cost=FeintCostDTO(tactics={"hit": 5, "dodge": 3, "crit": 2, "tempo": 2}),
        target=TargetType.ALL_ENEMIES,
        target_count=99,
        secondary_damage_mult=0.40,
        applicability_tags=[
            *_FENCING_TAGS,
            "hit",
            "dodge",
            "crit",
            "tempo",
            "damage",
            "multi_target",
            "anti_parry",
            "punish",
            "high_cost",
        ],
        purchase_group="weapon",
        pipeline_mutations=[
            pipeline_mutation("accuracy_mult", 0.85),
            pipeline_mutation("target_parry_mult", 0.65),
        ],
    ),
}

_FENCING_TEXTS = {
    "fencing_precise_prick": (
        "Точный укол",
        "собирая короткую точную линию провести точный укол",
        "Оружейный финт фехтования: следующий укол получает повышенную точность.",
        "собирая короткую точную линию",
        "и проводит точный укол",
        "и попадает в открытую точку",
    ),
    "fencing_corner_entry": (
        "Вход под углом",
        "входя под углом превратить смещение в критическое окно",
        "Оружейный финт фехтования: следующий удар получает повышенный шанс крита.",
        "входя под углом после смещения",
        "и находит окно для точного укола",
        "и превращает смещение в критическое окно",
    ),
    "fencing_hidden_entry": (
        "Скрытый вход",
        "пряча вход гарантировать критический укол",
        "Оружейный финт фехтования: следующий удар становится критическим и сложнее уходит в уворот.",
        "пряча вход за движением корпуса",
        "и наносит скрытый критический укол",
        "и раскрывает критический вход",
    ),
    "fencing_gap_probe": (
        "Проба щели",
        "нащупывая щель пробить броню и подготовить парирование",
        "Оружейный финт фехтования: следующий удар получает шанс пройти плоскую броню, а вы усиливаете парирование.",
        "нащупывая щель в защите",
        "и проверяет броню точным уколом",
        "и оставляет клинок готовым к парированию",
    ),
    "fencing_needle_gap": (
        "Игольная щель",
        "вводя клинок в игольную щель пройти мимо брони и поднять парирование",
        "Оружейный финт фехтования: следующий удар игнорирует плоскую броню, а вы сильнее усиливаете парирование.",
        "вводя клинок в игольную щель",
        "и проходит мимо плоской брони",
        "и выходит из прокола в сильное парирование",
    ),
    "fencing_slip_guard": (
        "Скользящая гарда",
        "скользя гардой подготовить переход парирования в уворот",
        "Оружейный финт фехтования: после подготовки следующий размен усиливает ваш уворот.",
        "скользя гардой на внешнюю линию",
        "и сохраняет корпус для ухода",
        "и переводит защиту в движение",
    ),
    "fencing_inside_line": (
        "Внутренняя линия",
        "ныряя во внутреннюю линию пройти мимо парирования и поднять уворот",
        "Оружейный финт фехтования: следующий удар игнорирует парирование, а вы сильнее усиливаете уворот.",
        "ныряя во внутреннюю линию",
        "и проходит мимо парирующего клинка",
        "и уходит с линии после прокола",
    ),
    "fencing_line_flurry": (
        "Серия по линии",
        "проводя серию коротких уколов задеть три цели",
        "Оружейный финт фехтования: основной укол задевает до двух дополнительных целей.",
        "проводя серию коротких уколов",
        "и цепляет соседнюю линию",
        "и прошивает несколько открытых окон",
    ),
    "fencing_storm_lattice": (
        "Решетка штормовых уколов",
        "разворачивая клинок прошить штормовой решеткой весь строй",
        "Оружейный финт фехтования: основной укол расходится по всем врагам сниженной точностью и снижает их парирование.",
        "разворачивая клинок в штормовую решетку",
        "и прошивает строй решеткой уколов",
        "и накрывает весь строй штормом уколов",
    ),
    "fencing_corner_entry_advanced": (
        "Карательный вход под углом",
        "наказывая промах противника войти под углом и раскрыть его защиту",
        "Карательный финт фехтования: тратит темп, повышает шанс крита и режет парирование цели.",
        "наказывая промах противника входом под углом",
        "и раскрывает защиту цели точным углом",
        "и раскрывает защиту цели критическим углом",
    ),
    "fencing_hidden_entry_advanced": (
        "Карательный скрытый вход",
        "наказывая промах противника войти скрытым уколом и сорвать защиту",
        "Карательный финт фехтования: тратит темп, критический удар проходит мимо уворота и сильно режет парирование цели.",
        "наказывая промах противника скрытым входом",
        "и пробивает защиту скрытым критическим уколом",
        "и срывает защиту цели скрытым критом",
    ),
    "fencing_storm_lattice_advanced": (
        "Карательная штормовая решетка",
        "наказывая весь строй прошить его штормовой решеткой и сбить парирование",
        "Карательный финт фехтования: тратит темп, основной укол расходится по всем врагам и сильно режет их парирование.",
        "наказывая весь строй штормовой решеткой",
        "и прошивает строй и сбивает парирование всем",
        "и сбивает парирование всему строю штормовой решеткой",
    ),
}


def _fencing_description(feint_id: str) -> CombatDescriptionDTO:
    display_name, ui_label, short, use_suffix, hit, crit = _FENCING_TEXTS[feint_id]
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
            miss=["но укол проходит мимо"],
            dodge=["но {target} уходит с линии укола"],
            parry=["но {target} отводит острие"],
            block=["но {target} закрывает линию"],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=[f"{{source}} атакует {{target}}, {use_suffix}"],
            hit=[hit],
            crit=[crit],
            miss=["но укол проходит мимо"],
            dodge=["но {target} уходит с линии укола"],
            parry=["но {target} сбивает острие движением"],
            block=["но укол гаснет о защиту {target}"],
        ),
    )


WEAPON_FENCING_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=_fencing_description(feint_id),
    )
    for feint_id, technical in WEAPON_FENCING_FEINTS_TECHNICAL.items()
}
