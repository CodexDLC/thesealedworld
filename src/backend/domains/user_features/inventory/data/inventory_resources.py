from src.shared.enums.inventory_enums import InventoryActionType, InventorySection, InventoryViewTarget
from src.shared.enums.item_enums import EquippedSlot
from src.shared.schemas.inventory import ButtonDTO


class InventoryResources:
    """
    Ресурсы инвентаря: Тексты и Фабрики кнопок.
    Отдает "чистые" тексты без эмодзи (эмодзи добавляет клиент).
    """

    # --- TEXTS (Pure) ---
    TITLE_MAIN = "Экипировка"
    TITLE_BAG = "Сумка"

    # Названия слотов (для заголовков и кнопок)
    SLOT_NAMES: dict[str, str] = {
        EquippedSlot.HEAD_ARMOR: "Голова",
        EquippedSlot.CHEST_ARMOR: "Тело",
        EquippedSlot.ARMS_ARMOR: "Руки",
        EquippedSlot.LEGS_ARMOR: "Ноги",
        EquippedSlot.FEET_ARMOR: "Ступни",
        EquippedSlot.CHEST_GARMENT: "Одежда",
        EquippedSlot.LEGS_GARMENT: "Штаны",
        EquippedSlot.OUTER_GARMENT: "Плащ",
        EquippedSlot.GLOVES_GARMENT: "Перчатки",
        EquippedSlot.MAIN_HAND: "Осн. рука",
        EquippedSlot.OFF_HAND: "Вт. рука",
        EquippedSlot.TWO_HAND: "Двуручн.",
        EquippedSlot.AMULET: "Амулет",
        EquippedSlot.EARRING: "Серьга",
        EquippedSlot.RING_1: "Кольцо 1",
        EquippedSlot.RING_2: "Кольцо 2",
        EquippedSlot.BELT_ACCESSORY: "Пояс",
    }

    # Названия разделов
    SECTION_NAMES: dict[str, str] = {
        InventorySection.EQUIPMENT: "Экипировка",
        InventorySection.CONSUMABLE: "Расходники",
        InventorySection.RESOURCE: "Ресурсы",
        InventorySection.QUEST: "Квестовые",
    }

    # Названия категорий (фильтров)
    CATEGORY_NAMES: dict[str, dict[str, str]] = {
        InventorySection.EQUIPMENT: {
            "weapon": "Оружие",
            "armor": "Броня",
            "garment": "Одежда",
            "accessory": "Аксессуары",
        },
        InventorySection.RESOURCE: {
            "ores": "Руды",
            "leathers": "Кожа",
            "fabrics": "Ткани",
            "organics": "Органика",
        },
        # Добавить остальные по мере необходимости
    }

    # --- BUTTON FACTORIES ---

    @staticmethod
    def get_slot_grid_buttons() -> list[list[ButtonDTO]]:
        """
        Возвращает сетку кнопок для слотов экипировки (для экрана Куклы).
        Структура 3 колонки.
        """
        # Порядок кнопок (как в старом UI)
        layout = [
            (EquippedSlot.HEAD_ARMOR, EquippedSlot.CHEST_GARMENT, EquippedSlot.AMULET),
            (EquippedSlot.CHEST_ARMOR, EquippedSlot.OUTER_GARMENT, EquippedSlot.BELT_ACCESSORY),
            (EquippedSlot.MAIN_HAND, EquippedSlot.OFF_HAND, EquippedSlot.TWO_HAND),
            (EquippedSlot.LEGS_ARMOR, EquippedSlot.FEET_ARMOR, EquippedSlot.RING_1),
            (EquippedSlot.ARMS_ARMOR, EquippedSlot.GLOVES_GARMENT, EquippedSlot.RING_2),
        ]

        grid = []
        for row in layout:
            grid_row = []
            for slot in row:
                text = InventoryResources.SLOT_NAMES.get(slot, str(slot))
                # Сокращаем длинные названия для кнопок, если нужно (клиент может переопределить)
                # Но пока отдаем как есть, клиент сам решит.

                grid_row.append(
                    ButtonDTO(
                        text=text,
                        action=InventoryViewTarget.BAG,  # Клик по слоту ведет в сумку с фильтром
                        payload={
                            "section": InventorySection.EQUIPMENT,
                            "category": str(slot.value),
                            "filter_type": "slot",
                        },
                    )
                )
            grid.append(grid_row)

        return grid

    @staticmethod
    def get_section_buttons() -> list[ButtonDTO]:
        """
        Кнопки перехода в разделы (Расходники, Ресурсы).
        """
        return [
            ButtonDTO(
                text=InventoryResources.SECTION_NAMES[InventorySection.CONSUMABLE],
                action=InventoryViewTarget.BAG,
                payload={"section": InventorySection.CONSUMABLE, "category": "all"},
            ),
            ButtonDTO(
                text=InventoryResources.SECTION_NAMES[InventorySection.RESOURCE],
                action=InventoryViewTarget.BAG,
                payload={"section": InventorySection.RESOURCE, "category": "all"},
            ),
        ]

    @staticmethod
    def get_filter_buttons(section: str, active_category: str | None) -> list[ButtonDTO]:
        """
        Кнопки фильтров для списка предметов.
        """
        buttons = []
        categories = InventoryResources.CATEGORY_NAMES.get(section, {})

        # Кнопка "Все"
        buttons.append(
            ButtonDTO(
                text="Все",
                action=InventoryViewTarget.BAG,
                payload={"section": section, "category": "all"},
                is_active=(active_category == "all" or active_category is None),
                style="primary" if active_category == "all" else "secondary",
            )
        )

        for cat_key, cat_name in categories.items():
            buttons.append(
                ButtonDTO(
                    text=cat_name,
                    action=InventoryViewTarget.BAG,
                    payload={"section": section, "category": cat_key},
                    is_active=(active_category == cat_key),
                    style="primary" if active_category == cat_key else "secondary",
                )
            )

        return buttons

    @staticmethod
    def get_item_actions(item_id: int, is_equipped: bool, item_type: str) -> list[ButtonDTO]:
        """
        Возвращает доступные действия для предмета.
        """
        actions = []

        if is_equipped:
            actions.append(
                ButtonDTO(
                    text="Снять", action=InventoryActionType.UNEQUIP, payload={"item_id": item_id}, style="danger"
                )
            )
        else:
            # Логика доступности действий зависит от типа
            if item_type in ["weapon", "armor", "accessory"]:
                actions.append(
                    ButtonDTO(
                        text="Надеть", action=InventoryActionType.EQUIP, payload={"item_id": item_id}, style="primary"
                    )
                )
            elif item_type == "consumable":
                actions.append(
                    ButtonDTO(
                        text="Использовать",
                        action=InventoryActionType.USE,
                        payload={"item_id": item_id},
                        style="primary",
                    )
                )

        # Общие действия
        actions.append(
            ButtonDTO(text="Выбросить", action=InventoryActionType.DROP, payload={"item_id": item_id}, style="danger")
        )

        return actions
