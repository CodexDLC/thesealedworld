import time
from typing import TypedDict

from src.shared.schemas.account_context import StatsDict, VitalsDict


class RegenResult(TypedDict):
    stats: StatsDict
    is_changed: bool


def calculate_regen(stats: StatsDict) -> RegenResult:
    """
    Рассчитывает регенерацию HP, MP, Stamina на основе прошедшего времени и сохраненной скорости регена.
    Использует time.time() (Unix Timestamp).

    Args:
        stats: Текущие статы (включая last_update и regen rates).

    Returns:
        RegenResult: Обновленные статы и флаг изменений.
    """
    now = time.time()
    last_update = stats.get("last_update")

    # Инициализация
    if last_update is None:
        stats["last_update"] = now
        return {"stats": stats, "is_changed": True}

    delta = now - last_update

    if delta <= 0:
        return {"stats": stats, "is_changed": False}

    is_changed = False

    # Helper function
    def apply_regen(vitals: VitalsDict, dt: float) -> bool:
        """Возвращает True, если значение изменилось."""
        current = vitals["cur"]
        maximum = vitals["max"]
        rate = vitals.get("regen", 0.0)  # Если регена нет, то 0

        if current >= maximum and rate > 0:
            return False

        # Если реген отрицательный (яд/горение), то можно и уменьшать, но пока считаем только восстановление
        # Или разрешаем уходить в минус? Пока ограничимся восстановлением до макс.

        gain = rate * dt
        new_val = min(maximum, int(current + gain))

        # TODO: Обработка смерти от отрицательного регена? Пока нет.
        new_val = max(0, new_val)

        if new_val != current:
            vitals["cur"] = new_val
            return True
        return False

    # Применяем ко всем виталам
    if apply_regen(stats["hp"], delta):
        is_changed = True

    if apply_regen(stats["mp"], delta):
        is_changed = True

    if apply_regen(stats["stamina"], delta):
        is_changed = True

    # Финализация
    if is_changed:
        stats["last_update"] = now

    # Важно: Если изменений не было (например, HP полное), мы НЕ обновляем last_update.
    # Это позволяет "накапливать" время. Если прошло 0.1 сек, а реген 1 ед/сек, то gain=0.1 -> int(0).
    # Если обновить last_update, то эти 0.1 сек пропадут.
    # Если НЕ обновить, то в следующий раз delta будет 0.2, потом 1.0 -> и тогда прибавится +1 HP.

    return {"stats": stats, "is_changed": is_changed}
