from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NpcDefinition:
    npc_key: str
    display_name: str
    role: str
    avatar_url: str | None = None
    tags: tuple[str, ...] = ()
    dialogue_quest_keys: tuple[str, ...] = ()
    home_location_id: str | None = None


_NPC_CATALOG: dict[str, NpcDefinition] = {
    "portal_pad_guide": NpcDefinition(
        npc_key="portal_pad_guide",
        display_name="Проводник Круга",
        role="PORTAL PAD GUIDE",
        avatar_url=None,
        tags=("portal_pad", "first_contact", "death_explainer"),
        dialogue_quest_keys=("awakening_rift", "first_death_portal_dialogue"),
        home_location_id="52_52",
    ),
    "tavern_bartender": NpcDefinition(
        npc_key="tavern_bartender",
        display_name="Кормчий Последнего Приюта",
        role="TAVERN BARTENDER",
        avatar_url=None,
        tags=("tavern", "bartender", "rumors", "lodging"),
        dialogue_quest_keys=("tavern_bartender_dialogue",),
        home_location_id="53_53",
    ),
    "tavern_keeper": NpcDefinition(
        npc_key="tavern_keeper",
        display_name="Старший по двору",
        role="TAVERN KEEPER",
        avatar_url=None,
        tags=("tavern", "keeper", "lodging"),
        dialogue_quest_keys=(),
        home_location_id="53_53",
    ),
}


def get_npc_definition(npc_key: str) -> NpcDefinition | None:
    return _NPC_CATALOG.get(npc_key)


def list_npc_definitions() -> tuple[NpcDefinition, ...]:
    return tuple(_NPC_CATALOG.values())
