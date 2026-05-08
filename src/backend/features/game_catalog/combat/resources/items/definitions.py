from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType
from src.backend.features.game_catalog.combat.resources.items.schemas import (
    CombatItemActionCatalogEntryDTO,
    CombatItemActionKind,
    CombatItemActionTechnicalDTO,
)

COMBAT_ITEM_ACTIONS_TECHNICAL = {
    "fire_grenade": CombatItemActionTechnicalDTO(
        item_action_id="fire_grenade",
        base_item_id="fire_grenade",
        ability_id="fireball",
        kind=CombatItemActionKind.GRENADE,
        target=TargetType.ALL_ENEMIES,
        target_count=3,
        effects=[{"id": "dot_burn", "params": {"duration": 2}}],
    ),
    "minor_healing_potion": CombatItemActionTechnicalDTO(
        item_action_id="minor_healing_potion",
        base_item_id="minor_healing_potion",
        ability_id="heal",
        kind=CombatItemActionKind.CONSUMABLE,
        target=TargetType.SELF,
        effects=[{"id": "restore_hp", "params": {"value": 25}}],
    ),
}


COMBAT_ITEM_ACTIONS_DESCRIPTIVE = {
    "fire_grenade": build_combat_description(
        resource_type="items",
        resource_id="fire_grenade",
        icon="combat/items/fire_grenade.svg",
        display_name="Огненная граната",
        ui_label="Разбить огненную гранату",
        short_description="Расходник, который наносит огненный урон по группе целей.",
        humanoid_long_description="Хрупкая колба с нестабильным жаром: при ударе огонь расплескивается по ближайшим целям.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} разбивает {item} у ног {target}"],
            hit=["огонь накрывает {target}"],
            miss=["но {target} выходит из огня"],
            apply_effect=["пламя оставляет на {target} эффект {effect}"],
            area_use=["{source} разбивает {item}"],
            area_result=["огонь расплескивается по {targets_count} целям"],
            no_resource=["{source} тянется к {item}, но не может использовать предмет"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
    "minor_healing_potion": build_combat_description(
        resource_type="items",
        resource_id="minor_healing_potion",
        icon="combat/items/minor_healing_potion.svg",
        display_name="Малое лечебное зелье",
        ui_label="Выпить малое лечебное зелье",
        short_description="Расходник, который восстанавливает немного здоровья.",
        humanoid_long_description="Простое зелье первой помощи, возвращающее телу немного сил прямо в бою.",
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} выпивает {item}"],
            heal=["{item} возвращает силы {source}"],
            no_resource=["{source} не может использовать {item}"],
        ),
        beast_event_texts=CombatEventTextSetDTO(),
    ),
}


COMBAT_ITEM_ACTIONS_CATALOG = {
    item_action_id: CombatItemActionCatalogEntryDTO(
        key=f"combat.item.{item_action_id}",
        technical=technical,
        descriptive=COMBAT_ITEM_ACTIONS_DESCRIPTIVE[item_action_id],
    )
    for item_action_id, technical in COMBAT_ITEM_ACTIONS_TECHNICAL.items()
}
