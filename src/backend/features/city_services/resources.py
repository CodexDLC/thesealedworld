from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CityServiceSection:
    id: str
    title: str
    description: str
    icon: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CityServiceDefinition:
    service_id: str
    service_type: str
    title: str
    description: str
    background_url: str | None = None
    sections: tuple[CityServiceSection, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


CITY_SERVICE_DEFINITIONS: dict[str, CityServiceDefinition] = {
    "svc_tavern_hub": CityServiceDefinition(
        service_id="svc_tavern_hub",
        service_type="tavern",
        title="Постоялый двор Последний Приют",
        description=(
            "Древнее здание с десятками комнат приспособили под постоялый двор. "
            "Внизу работает таверна, у стойки кормчий ведет ключи, пайки и первые правила ночлега."
        ),
        sections=(
            CityServiceSection(
                "bar", "Стойка кормчего", "У стойки держат первые слухи, ключи, пайки и договоренности.", "talk"
            ),
            CityServiceSection(
                "room",
                "Личная комната",
                "Одна из уцелевших комнат наверху; часть соседних помещений все еще без крыши.",
                "bed",
            ),
            CityServiceSection(
                "common_hall", "Таверна", "Теплый нижний зал со столами, едой, слухами и местной активностью.", "users"
            ),
        ),
        metadata={
            "tavern_id": "last_refuge",
            "room_key": "last_refuge_private_room",
            "bartender_key": "tavern_bartender",
            "npc_key": "tavern_bartender",
            "dialogue_quest_key": "tavern_bartender_dialogue",
        },
    ),
    "svc_portal_hub": CityServiceDefinition(
        service_id="svc_portal_hub",
        service_type="portal",
        title="Площадь Рунного Круга",
        description=(
            "Внутри рунического круга слышен ровный низкий гул. Камни держат стабильный контур, "
            "а закрытые проходы ждут калибровки."
        ),
        background_url="/static/images/exploration/city/d4/52_52_runic_circle_plaza.png",
        metadata={
            "npc_key": "portal_pad_guide",
            "dialogue_quest_key": "awakening_rift",
            "dialogue_section_id": "portal_contact",
            "npc": {
                "id": "portal_first_contact",
                "npc_key": "portal_pad_guide",
                "name": "Проводник Круга",
                "role": "FIRST CONTACT",
                "stage_position": "bottom-right",
                "dialogue_quest_key": "awakening_rift",
            },
        },
    ),
    "svc_town_hall_hub": CityServiceDefinition(
        service_id="svc_town_hall_hub",
        service_type="town_hall",
        title="Совет поселения",
        description="Совет поселения принимает только срочные обращения. Доски законов и заявок еще приводят в порядок.",
    ),
    "svc_blacksmith_repair": CityServiceDefinition(
        service_id="svc_blacksmith_repair",
        service_type="workshop.blacksmith",
        title="Старый горн",
        description=(
            "Ремесленный двор у южной стены запускает ремонтный горн. Уголь уже горит, материалы сложены под навесами, "
            "но полноценные заказы пока не принимаются."
        ),
    ),
    "svc_market_hub": CityServiceDefinition(
        service_id="svc_market_hub",
        service_type="market",
        title="Торговый зал Старого Распорядка",
        description=(
            "Старое административное здание приспособили под торговый узел: здесь готовят аукционные доски, "
            "временные палатки и первые лавки, которые игроки смогут открывать в расчищенных нишах."
        ),
    ),
}


def get_city_service_definition(service_id: str) -> CityServiceDefinition:
    try:
        return CITY_SERVICE_DEFINITIONS[service_id]
    except KeyError as exc:
        raise ValueError(f"Unknown city service_id: {service_id}") from exc


def get_tavern_definition(tavern_id: str) -> CityServiceDefinition:
    for definition in CITY_SERVICE_DEFINITIONS.values():
        if definition.metadata.get("tavern_id") == tavern_id:
            return definition
    raise ValueError(f"Unknown tavern_id: {tavern_id}")
