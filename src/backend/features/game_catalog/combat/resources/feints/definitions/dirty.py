from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.feints.schemas import (
    FeintCatalogEntryDTO,
    FeintConfigDTO,
    FeintCostDTO,
    FeintTechnicalDTO,
)

DIRTY_FEINTS_TECHNICAL = {
    "sand_throw": FeintTechnicalDTO(
        feint_id="sand_throw",
        cost=FeintCostDTO(tactics={"tempo": 3}),
        target=TargetType.SINGLE_ENEMY,
        raw_mutations={"physical_damage_mult": "-0.8"},
        effects=[{"id": "blind", "params": {"duration": 2}}],
    ),
    "low_blow": FeintTechnicalDTO(
        feint_id="low_blow",
        cost=FeintCostDTO(tactics={"crit": 2}),
        target=TargetType.SINGLE_ENEMY,
        triggers=["control.stun_on_hit"],
    ),
}

DIRTY_FEINTS_DESCRIPTIVE = {
    "sand_throw": build_combat_description(
        resource_type="feints",
        resource_id="sand_throw",
        icon="combat/feints/sand_throw.svg",
        display_name="Бросок песка",
        ui_label="Поймать момент и бросить песок в глаза",
        short_description="Ослепляет противника, снижая его точность.",
        humanoid_long_description=(
            "Грязный прием: исполнитель ловит короткую паузу в размене и бросает песок в лицо цели, "
            "чтобы сорвать защитную реакцию."
        ),
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} ловит момент и бросает песок в глаза {target}"],
            hit=["и попадает, заставляя {target} сбиться с защиты."],
            crit=["и ослепляет {target} в самый опасный момент."],
            miss=["но {target} отворачивается, и песок летит мимо."],
            block=["но {target} закрывается рукой и щитом от грязного приема."],
            parry=["но {target} сбивает руку {source} до броска."],
            dodge=["но {target} уходит от грязного приема."],
            apply_effect=["{target} получает эффект {effect}."],
            expire_effect=["{target} снова видит достаточно ясно."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} бросает горсть песка в морду {target}"],
            hit=["и песок попадает в глаза {target}."],
            crit=["и {target} мотает головой, теряя направление атаки."],
            miss=["но {target} мотает головой и избегает приема."],
            block=["но песок осыпается по корпусу {target} без толку."],
            parry=["но {target} сбивает движение рывком."],
            dodge=["но {target} уходит от броска."],
            apply_effect=["{target} получает эффект {effect}."],
            expire_effect=["{target} снова ориентируется в бою."],
        ),
    ),
    "low_blow": build_combat_description(
        resource_type="feints",
        resource_id="low_blow",
        icon="combat/feints/low_blow.svg",
        display_name="Подлый удар",
        ui_label="Ударить ниже защиты, пока цель раскрыта",
        short_description="Болезненный удар, который может оглушить.",
        humanoid_long_description=(
            "Грязный ближний прием: исполнитель бьет в уязвимое место, когда цель открывается в размене."
        ),
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} бьет ниже защиты, пока {target} раскрыт"],
            hit=["и болезненно сбивает темп {target}."],
            crit=["и заставляет {target} потерять дыхание от удара."],
            miss=["но {target} успевает убрать корпус."],
            block=["но {target} закрывает уязвимую линию."],
            parry=["но {target} перехватывает движение до удара."],
            dodge=["но {target} отступает от подлого приема."],
            apply_effect=["{target} получает эффект {effect}."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} бьет в уязвимое место {target}"],
            hit=["и сбивает движение {target}."],
            crit=["и резко ломает темп атаки {target}."],
            miss=["но {target} уходит рывком."],
            block=["но удар гаснет о корпус {target}."],
            parry=["но {target} сбивает движение корпусом."],
            dodge=["но {target} отскакивает от приема."],
            apply_effect=["{target} получает эффект {effect}."],
        ),
    ),
}

DIRTY_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=DIRTY_FEINTS_DESCRIPTIVE[feint_id],
    )
    for feint_id, technical in DIRTY_FEINTS_TECHNICAL.items()
}

DIRTY_FEINTS = [FeintConfigDTO.from_catalog_entry(entry) for entry in DIRTY_FEINTS_CATALOG.values()]
