from src.backend.features.game_catalog.combat.resources.basic_exchanges.schemas import (
    BasicExchangeCatalogEntryDTO,
    BasicExchangeTechnicalDTO,
)
from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)


def _make_entry(
    *,
    exchange_id: str,
    source_type: str,
    weapon_class: str,
    hand: str,
    display_name: str,
    short_description: str,
) -> BasicExchangeCatalogEntryDTO:
    event_texts = CombatEventTextSetDTO(
        use=["{source} атакует {target} {natural_weapon}"],
        hit=["и попадает, нанося {damage} урона"],
        crit=["и вцепляется особенно точно, нанося {damage} урона"],
        miss=["но промахивается"],
        dodge=["но {target} уходит с линии атаки"],
        parry=["но {target} сбивает атаку"],
        block=["но {target} принимает удар на защиту"],
    )
    return BasicExchangeCatalogEntryDTO(
        key=f"combat.basic_exchange.{exchange_id}",
        technical=BasicExchangeTechnicalDTO(
            exchange_id=exchange_id,
            skill_key="natural_weapon",
            source_type=source_type,
            weapon_class=weapon_class,
            hand=hand,
        ),
        descriptive=build_combat_description(
            resource_type="basic_exchange",
            resource_id=exchange_id,
            display_name=display_name,
            short_description=short_description,
            humanoid_event_texts=event_texts,
            beast_event_texts=event_texts,
        ),
    )


NATURAL_WEAPON_BASIC_EXCHANGES_CATALOG: dict[str, BasicExchangeCatalogEntryDTO] = {
    "natural_weapon.fangs.main_hand": _make_entry(
        exchange_id="natural_weapon.fangs.main_hand",
        source_type="main_hand",
        weapon_class="fangs",
        hand="main",
        display_name="Укус",
        short_description="Базовая атака клыками или зубами.",
    ),
    "natural_weapon.fangs.off_hand": _make_entry(
        exchange_id="natural_weapon.fangs.off_hand",
        source_type="off_hand",
        weapon_class="fangs",
        hand="off",
        display_name="Боковой укус",
        short_description="Вспомогательная атака клыками или зубами.",
    ),
    "natural_weapon.claws.main_hand": _make_entry(
        exchange_id="natural_weapon.claws.main_hand",
        source_type="main_hand",
        weapon_class="claws",
        hand="main",
        display_name="Удар когтями",
        short_description="Базовая атака когтями или лапами.",
    ),
    "natural_weapon.claws.off_hand": _make_entry(
        exchange_id="natural_weapon.claws.off_hand",
        source_type="off_hand",
        weapon_class="claws",
        hand="off",
        display_name="Удар второй лапой",
        short_description="Вспомогательная атака когтями или лапами.",
    ),
    "natural_weapon.default.main_hand": _make_entry(
        exchange_id="natural_weapon.default.main_hand",
        source_type="main_hand",
        weapon_class="default",
        hand="main",
        display_name="Естественная атака",
        short_description="Базовая атака естественным оружием существа.",
    ),
    "natural_weapon.default.off_hand": _make_entry(
        exchange_id="natural_weapon.default.off_hand",
        source_type="off_hand",
        weapon_class="default",
        hand="off",
        display_name="Вспомогательная естественная атака",
        short_description="Вспомогательная атака естественным оружием существа.",
    ),
}
