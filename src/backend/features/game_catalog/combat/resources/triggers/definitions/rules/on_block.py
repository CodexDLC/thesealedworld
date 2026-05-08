from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
    default_trigger_proc_event_texts,
)
from src.backend.features.game_catalog.combat.resources.triggers.schemas import (
    TriggerCatalogEntryDTO,
    TriggerTechnicalDTO,
)

ON_BLOCK_CATALOG: list[TriggerCatalogEntryDTO] = [
    TriggerCatalogEntryDTO(
        key="combat.trigger.block.bash_on_block",
        technical=TriggerTechnicalDTO(
            trigger_id="bash_on_block",
            event="ON_BLOCK",
            chance=1.0,
            mutations={"chain_events.trigger_extra_strike": True},
        ),
        descriptive=build_combat_description(
            resource_type="trigger",
            resource_id="bash_on_block",
            display_name="Удар щитом (блок)",
            short_description="Успешный блок наносит ответный удар щитом.",
            humanoid_event_texts=CombatEventTextSetDTO(
                block_proc=[
                    "{target} блокирует удар {source} и отвечает щитом.",
                ],
                extra_strike=["{target} добавляет удар щитом."],
            ),
            beast_event_texts=default_trigger_proc_event_texts("Удар щитом (блок)"),
        ),
    ),
]
