from .swords import SWORDS_DB

# Собираем все базы оружия в одну
WEAPONS_DB = {
    **SWORDS_DB,
    # В будущем сюда добавятся:
    # **AXES_DB,
    # **MACES_DB,
    # **BOWS_DB,
}

__all__ = ["WEAPONS_DB"]
