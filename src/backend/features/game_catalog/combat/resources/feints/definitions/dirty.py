from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    build_combat_description,
    default_feint_event_texts,
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
        display_name="Бросок песка",
        short_description="Ослепляет противника, снижая его точность.",
        humanoid_event_texts=default_feint_event_texts("Бросок песка"),
        beast_event_texts=default_feint_event_texts("Бросок песка"),
    ),
    "low_blow": build_combat_description(
        resource_type="feints",
        resource_id="low_blow",
        display_name="Подлый удар",
        short_description="Болезненный удар, который может оглушить.",
        humanoid_event_texts=default_feint_event_texts("Подлый удар"),
        beast_event_texts=default_feint_event_texts("Подлый удар"),
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
