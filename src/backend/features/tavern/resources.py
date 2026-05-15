from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TavernConfig:
    tavern_id: str
    service_id: str
    title: str
    description: str
    room_key: str
    bartender_key: str
    dialogue_quest_key: str


TAVERN_CONFIGS: dict[str, TavernConfig] = {
    "last_refuge": TavernConfig(
        tavern_id="last_refuge",
        service_id="svc_tavern_hub",
        title="Таверна Последнее Убежище",
        description="Теплый шум, грубые столы и стойка, за которой уже собирают первые правила нового города.",
        room_key="last_refuge_private_room",
        bartender_key="last_refuge_bartender",
        dialogue_quest_key="tavern_bartender_dialogue",
    )
}


def get_tavern_config(tavern_id: str) -> TavernConfig:
    try:
        return TAVERN_CONFIGS[tavern_id]
    except KeyError as exc:
        raise ValueError(f"Unknown tavern_id: {tavern_id}") from exc
