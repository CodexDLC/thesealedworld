from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
    default_trigger_proc_event_texts,
)
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import pipeline_mutation
from src.backend.features.game_catalog.combat.resources.triggers.schemas import (
    TriggerCatalogEntryDTO,
    TriggerTechnicalDTO,
)

ON_ACCURACY_CATALOG: list[TriggerCatalogEntryDTO] = [
    TriggerCatalogEntryDTO(
        key="combat.trigger.accuracy.true_strike",
        technical=TriggerTechnicalDTO(
            trigger_id="true_strike",
            event="ON_ACCURACY_CHECK",
            chance=1.0,
            pipeline_mutations=[pipeline_mutation("ignore_evasion")],
            allowed_sources=["weapon", "feint", "monster"],
            display_policy="merge",
            tags=["accuracy", "anti_evasion"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="true_strike",
            display_name="Верный удар",
            short_description="Игнорирует уклонение цели.",
            humanoid_event_texts=CombatEventTextSetDTO(
                proc=["{source} наносит неотвратимый удар по {target}."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Верный удар"),
        ),
    ),
    TriggerCatalogEntryDTO(
        key="combat.trigger.miss.rage_on_miss",
        technical=TriggerTechnicalDTO(
            trigger_id="rage_on_miss",
            event="ON_MISS",
            chance=1.0,
            allowed_sources=["weapon", "feint", "monster"],
            display_policy="merge",
            tags=["resource", "miss", "rage"],
            token_grants_attacker=["RAGE_TOKEN"],
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="rage_on_miss",
            display_name="Ярость берсерка",
            short_description="Промах усиливает следующую атаку.",
            humanoid_event_texts=CombatEventTextSetDTO(
                miss_proc=["{source} промахивается, но ярость нарастает."],
                token_gain=["{source} получает токен ярости."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Ярость берсерка"),
        ),
    ),
]
