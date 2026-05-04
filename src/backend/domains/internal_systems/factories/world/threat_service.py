from operator import itemgetter
from typing import TypedDict

from src.backend.resources.game_data.graf_data_world.world_config import (
    ANCHORS,
    HUB_CENTER,
    HYBRID_TAGS,
    INFLUENCE_TAGS,
    PORTAL_PARAMS,
)


class _Influence(TypedDict):
    tags: list[str]
    val: float
    type: str  # 'north_prime', 'south_prime' и т.д.


class ThreatService:
    """
    Сервис расчета уровня угрозы на основе 'Полевой Теории'.
    Исправлен для жесткой защиты Хаба (D4).
    """

    TYPE_MAP = {
        "north_prime": "ice",
        "south_prime": "fire",
        "west_prime": "gravity",
        "east_prime": "bio",
    }

    # Границы региона D4 (15x15) относительно центра (52, 52)
    # Радиус = 7 (т.е. от 45 до 59 включительно)
    CITY_RADIUS = 7

    @staticmethod
    def calculate_threat(x: int, y: int) -> float:
        """
        Рассчитывает уровень угрозы (0.0 - 1.0).
        Внутри города угроза искусственно занижается.
        """
        dist_hub = ThreatService._get_dist(x, y, HUB_CENTER["x"], HUB_CENTER["y"])

        # Базовая защита портала
        stability = PORTAL_PARAMS["power"] / (1 + dist_hub * PORTAL_PARAMS["falloff"])

        danger = 0.0
        for anchor in ANCHORS:
            dist = ThreatService._get_dist(x, y, anchor["x"], anchor["y"])
            danger += anchor["power"] / (1 + dist * anchor["falloff"])

        # 🔥 ЖЕСТКОЕ ГАШЕНИЕ ВНУТРИ ГОРОДА 🔥
        if dist_hub <= ThreatService.CITY_RADIUS:
            # Внутри стен угроза падает еще сильнее (в 4 раза),
            # чтобы Threat Tier был 0 или 1 (безопасно/тревожно), но не смертельно.
            danger *= 0.25

        total = danger - stability
        return max(0.0, min(1.0, total))

    @staticmethod
    def get_tier_from_threat(threat: float) -> int:
        if threat < 0.05:
            return 0
        if threat < 0.20:
            return 1
        if threat < 0.35:
            return 2
        if threat < 0.55:
            return 3
        if threat < 0.75:
            return 4
        if threat < 0.90:
            return 5
        if threat < 0.98:
            return 6
        return 7

    @staticmethod
    def get_narrative_tags(x: int, y: int) -> list[str]:
        """
        Возвращает список тегов влияния.
        """
        threat_val = ThreatService.calculate_threat(x, y)
        current_tier = ThreatService.get_tier_from_threat(threat_val)
        dist_hub = ThreatService._get_dist(x, y, HUB_CENTER["x"], HUB_CENTER["y"])

        # Проверка: Мы внутри города?
        is_inside_city = dist_hub <= ThreatService.CITY_RADIUS

        # --- SHIELD LOGIC (Модификатор силы тегов) ---
        shield_modifier = 1.0

        if is_inside_city:
            # Внутри города:
            shield_modifier = 0.0 if dist_hub <= 4 else 0.2
        else:
            # За стеной -> Линейное ослабление щита по мере удаления
            # На 8-й клетке (сразу за стеной) щит еще действует, но слабее
            distance_from_wall = dist_hub - ThreatService.CITY_RADIUS
            shield_modifier = distance_from_wall / 10.0 if distance_from_wall < 10 else 1.0

        if shield_modifier == 0.0:
            return []

        active_tags: list[str] = []
        influences: list[_Influence] = []

        for anchor in ANCHORS:
            dist = ThreatService._get_dist(x, y, anchor["x"], anchor["y"])
            # Рассчитываем силу влияния с учетом щита
            raw_influence = anchor["power"] / (1 + dist * anchor["falloff"])
            influence_val = raw_influence * shield_modifier

            # Порог вхождения. Внутри города он выше (0.1), снаружи ниже (0.05)
            threshold = 0.1 if is_inside_city else 0.05

            if influence_val > threshold:
                influences.append(
                    {
                        "tags": anchor["narrative_tags"],
                        "val": influence_val,
                        "type": anchor.get("type", "unknown"),
                    }
                )

        if not influences:
            return []

        influences.sort(key=itemgetter("val"), reverse=True)
        primary = influences[0]

        # 1. Основная стихия
        # Если мы в городе, форсируем Tier 1 (только косметические теги типа "frost"),
        # даже если threat calc выдал больше.
        effective_tier = 1 if is_inside_city else current_tier

        grad_tags = ThreatService._get_gradient_tags(primary["type"], effective_tier)
        if grad_tags:
            active_tags.extend(grad_tags)
        else:
            active_tags.extend(primary["tags"])

        # 2. 🔥 ГИБРИДЫ И СМЕШИВАНИЕ 🔥
        # Смешивание разрешено ТОЛЬКО ЗА ПРЕДЕЛАМИ ГОРОДА
        if not is_inside_city:
            secondary = influences[1] if len(influences) > 1 else None

            if secondary and secondary["val"] > 0.15 and secondary["val"] > (primary["val"] * 0.7):
                sec_tier = max(0, current_tier - 2)

                # Добавляем теги второй стихии
                grad_tags_sec = ThreatService._get_gradient_tags(secondary["type"], sec_tier)
                if grad_tags_sec:
                    active_tags.extend(grad_tags_sec)
                else:
                    active_tags.extend(secondary["tags"])

                # Уникальная реакция (Лед + Огонь и т.д.)
                key1 = ThreatService.TYPE_MAP.get(primary["type"])
                key2 = ThreatService.TYPE_MAP.get(secondary["type"])

                if key1 and key2:
                    combo_key = frozenset([key1, key2])
                    hybrid_reaction = HYBRID_TAGS.get(combo_key)
                    if hybrid_reaction:
                        active_tags.extend(hybrid_reaction)

        return list(dict.fromkeys(active_tags))

    @staticmethod
    def _get_gradient_tags(anchor_type: str, tier: int) -> list[str] | None:
        gradient_key = ThreatService.TYPE_MAP.get(anchor_type)
        if not gradient_key or gradient_key not in INFLUENCE_TAGS:
            return None

        tier_map = INFLUENCE_TAGS[gradient_key]
        for (min_t, max_t), tags in tier_map.items():
            if min_t <= tier <= max_t:
                return tags
        return None

    @staticmethod
    def _get_dist(x1: int, y1: int, x2: int, y2: int) -> float:
        # Манхэттенское расстояние или Чебышева (тут Чебышева - max, для квадратной сетки)
        return float(max(abs(x1 - x2), abs(y1 - y2)))
