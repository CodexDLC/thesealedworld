from __future__ import annotations

from typing import Any

COMBAT_TOKENS: dict[str, dict[str, Any]] = {
    "tempo": {
        "title": "Темп",
        "description": "Тактический ресурс боя. Используется для действий, которые меняют ритм размена.",
        "icon": "token-tempo",
        "order": 10,
    },
    "hit": {
        "title": "Попадание",
        "description": "Накопленный боевой ресурс за успешные попадания.",
        "icon": "token-hit",
        "order": 20,
    },
    "crit": {
        "title": "Крит",
        "description": "Ресурс, связанный с критическими ударами и усиленными приемами.",
        "icon": "token-crit",
        "order": 30,
    },
    "dodge": {
        "title": "Уклонение",
        "description": "Ресурс, получаемый от успешного ухода от атаки.",
        "icon": "token-dodge",
        "order": 40,
    },
    "parry": {
        "title": "Парирование",
        "description": "Ресурс, получаемый после успешного парирования удара.",
        "icon": "token-parry",
        "order": 50,
    },
    "block": {
        "title": "Блок",
        "description": "Ресурс, связанный с защитой и удержанием удара.",
        "icon": "token-block",
        "order": 60,
    },
    "counter": {
        "title": "Контратака",
        "description": "Ресурс для ответных действий после удачной защиты или ошибки противника.",
        "icon": "token-counter",
        "order": 70,
    },
    "gift": {
        "title": "Дар",
        "description": "Магический ресурс для способностей, связанных с даром персонажа.",
        "icon": "token-gift",
        "order": 80,
    },
}


def get_all_combat_tokens() -> dict[str, dict[str, Any]]:
    return COMBAT_TOKENS
