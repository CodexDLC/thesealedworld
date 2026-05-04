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

TACTICAL_FEINTS_TECHNICAL = {
    "true_strike": FeintTechnicalDTO(
        feint_id="true_strike",
        cost=FeintCostDTO(tactics={"hit": 2}),
        target=TargetType.SINGLE_ENEMY,
        triggers=["accuracy.true_strike"],
        raw_mutations={"physical_damage_mult": "-0.2"},
    ),
    "power_attack": FeintTechnicalDTO(
        feint_id="power_attack",
        cost=FeintCostDTO(tactics={"crit": 1, "hit": 1}),
        target=TargetType.SINGLE_ENEMY,
        raw_mutations={
            "physical_damage_mult": "+0.5",
            "accuracy_mult": "-0.2",
        },
    ),
    "defensive_strike": FeintTechnicalDTO(
        feint_id="defensive_strike",
        cost=FeintCostDTO(tactics={"tempo": 2}),
        target=TargetType.SINGLE_ENEMY,
        triggers=["dodge.counter_on_dodge"],
    ),
}

TACTICAL_FEINTS_DESCRIPTIVE = {
    "true_strike": build_combat_description(
        resource_type="feints",
        resource_id="true_strike",
        display_name="Верный удар",
        short_description="Игнорирует уклонение противника, но наносит меньше урона.",
        humanoid_event_texts=default_feint_event_texts("Верный удар"),
        beast_event_texts=default_feint_event_texts("Верный удар"),
    ),
    "power_attack": build_combat_description(
        resource_type="feints",
        resource_id="power_attack",
        display_name="Сильный удар",
        short_description="Наносит повышенный урон, но снижает точность.",
        humanoid_event_texts=default_feint_event_texts("Сильный удар"),
        beast_event_texts=default_feint_event_texts("Сильный удар"),
    ),
    "defensive_strike": build_combat_description(
        resource_type="feints",
        resource_id="defensive_strike",
        display_name="Осторожный удар",
        short_description="Удар с подготовкой к защите. Повышает шанс контратаки при уклонении.",
        humanoid_event_texts=default_feint_event_texts("Осторожный удар"),
        beast_event_texts=default_feint_event_texts("Осторожный удар"),
    ),
}

TACTICAL_FEINTS_CATALOG = {
    feint_id: FeintCatalogEntryDTO(
        key=f"combat.feint.{feint_id}",
        technical=technical,
        descriptive=TACTICAL_FEINTS_DESCRIPTIVE[feint_id],
    )
    for feint_id, technical in TACTICAL_FEINTS_TECHNICAL.items()
}

TACTICAL_FEINTS = [FeintConfigDTO.from_catalog_entry(entry) for entry in TACTICAL_FEINTS_CATALOG.values()]
