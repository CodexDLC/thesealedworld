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


TAVERN_BACKGROUND = "/static/images/exploration/city/d4/52_53_last_refuge_tavern.png"

CITY_SERVICE_DEFINITIONS: dict[str, CityServiceDefinition] = {
    "svc_tavern_hub": CityServiceDefinition(
        service_id="svc_tavern_hub",
        service_type="tavern",
        title="Таверна Последнее Убежище",
        description="Теплый шум, грубые столы и стойка, за которой уже собирают первые правила нового города.",
        background_url=TAVERN_BACKGROUND,
        sections=(
            CityServiceSection("bar", "Барная стойка", "За стойкой держат первые слухи, ключи и договоренности.", "talk"),
            CityServiceSection("room", "Личная комната", "Небольшая закрытая комната наверху.", "bed"),
            CityServiceSection("common_hall", "Общий зал", "Свободные столы ждут заявок групп и местной активности.", "users"),
        ),
        metadata={
            "tavern_id": "last_refuge",
            "room_key": "last_refuge_private_room",
            "bartender_key": "last_refuge_bartender",
            "dialogue_quest_key": "tavern_bartender_dialogue",
        },
    ),
    "svc_portal_hub": CityServiceDefinition(
        service_id="svc_portal_hub",
        service_type="portal",
        title="Площадь Рунного Круга",
        description="Портал обустраивается. Камни уже держат стабильный контур, но проходы пока закрыты для жителей.",
        background_url="/static/images/exploration/city/d4/52_52_runic_circle_plaza.png",
    ),
    "svc_town_hall_hub": CityServiceDefinition(
        service_id="svc_town_hall_hub",
        service_type="town_hall",
        title="Совет поселения",
        description="Совет поселения принимает только срочные обращения. Доски законов и заявок еще приводят в порядок.",
        background_url="/static/images/exploration/city/d4/51_52_elders_avenue.png",
    ),
    "svc_blacksmith_repair": CityServiceDefinition(
        service_id="svc_blacksmith_repair",
        service_type="workshop.blacksmith",
        title="Старый горн",
        description="Мастерская запускает ремонтный двор. Уголь уже горит, но полноценные заказы пока не принимаются.",
        background_url="/static/images/exploration/city/d4/51_52_elders_avenue.png",
    ),
    "svc_market_hub": CityServiceDefinition(
        service_id="svc_market_hub",
        service_type="market",
        title="Рыночная площадь",
        description="Рынок собирает торговцев. Прилавки уже расставлены, но торг и заказы еще ждут городских правил.",
        background_url="/static/images/exploration/city/d4/53_52_market_square.png",
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
