from typing import Any

from loguru import logger as log


class ShardTemplateReader:
    """
    Предоставляет удобный интерфейс для чтения данных из шаблона подземелья.

    Инкапсулирует логику доступа к различным частям словаря-шаблона,
    предоставляя типизированные методы для получения информации о комнатах,
    их свойствах и метаданных подземелья.
    """

    def __init__(self, dungeon_template: dict[str, Any]):
        """
        Инициализирует ShardTemplateReader с заданным шаблоном подземелья.

        Args:
            dungeon_template: Словарь, содержащий полную структуру шаблона подземелья.
        """
        self.template = dungeon_template
        try:
            name = self.template.get("dungeon_meta", {}).get("name", "N/A")
            level = self.template.get("dungeon_meta", {}).get("level", "?")
            rooms_count = len(self.template.get("rooms", {}))
            log.debug(f"ShardTemplateReader | status=initialized name='{name}' level={level} rooms={rooms_count}")
        except (KeyError, TypeError) as e:
            log.warning(f"ShardTemplateReader | status=warning reason='Failed to log metadata on init' error='{e}'")

    def get_room_description(self, room_id: str) -> str:
        """
        Возвращает текстовое описание для указанной комнаты.

        Args:
            room_id: Уникальный идентификатор комнаты.

        Returns:
            Строка с описанием комнаты.
        """
        data = self.template["rooms"][room_id]["description"]
        log.debug(f"ShardTemplateReader | action=get_room_description room_id='{room_id}' len={len(data)}")
        return data

    def get_room_name(self, room_id: str) -> str:
        """
        Возвращает название для указанной комнаты.

        Args:
            room_id: Уникальный идентификатор комнаты.

        Returns:
            Строка с названием комнаты.
        """
        data = self.template["rooms"][room_id]["name"]
        log.debug(f"ShardTemplateReader | action=get_room_name room_id='{room_id}' name='{data}'")
        return data

    def get_room_exits(self, room_id: str) -> dict[str, str]:
        """
        Возвращает словарь выходов из указанной комнаты.

        Args:
            room_id: Уникальный идентификатор комнаты.

        Returns:
            Словарь, где ключи - направления, а значения - ID комнат,
            в которые ведут эти выходы.
        """
        data = self.template["rooms"][room_id]["exits"]
        log.debug(f"ShardTemplateReader | action=get_room_exits room_id='{room_id}' exits='{data}'")
        return data

    def get_room_tags(self, room_id: str) -> list[str]:
        """
        Возвращает список тегов окружения для указанной комнаты.

        Args:
            room_id: Уникальный идентификатор комнаты.

        Returns:
            Список строк, представляющих теги.
        """
        data = self.template["rooms"][room_id]["environment_tags"]
        log.debug(f"ShardTemplateReader | action=get_room_tags room_id='{room_id}' tags='{data}'")
        return data

    def get_meta_rooms(self) -> dict[str, str]:
        """
        Возвращает словарь "мета-комнат" из метаданных подземелья.

        Мета-комнаты - это специальные комнаты, такие как стартовая комната
        или комната с боссом.

        Returns:
            Словарь, где ключи - это тип мета-комнаты (e.g., 'start_room'),
            а значения - ID соответствующей комнаты.
        """
        data = self.template["dungeon_meta"]["meta_rooms"]
        log.debug(f"ShardTemplateReader | action=get_meta_rooms meta_rooms='{data}'")
        return data

    def get_room_data(self, room_id: str) -> dict[str, Any]:
        """
        Возвращает полный "сырой" словарь для указанной комнаты.

        Этот метод полезен, когда требуется доступ ко всем данным комнаты,
        а не к какому-то конкретному полю.

        Args:
            room_id: Уникальный идентификатор комнаты.

        Returns:
            Словарь со всеми данными, относящимися к комнате.
        """
        data = self.template["rooms"][room_id]
        log.debug(f"ShardTemplateReader | action=get_room_data room_id='{room_id}'")
        return data
