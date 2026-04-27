from math import ceil

from src.backend.domains.user_features.inventory.data.inventory_resources import InventoryResources
from src.backend.domains.user_features.inventory.engine.dispatcher_bridge import InventoryDispatcherBridge
from src.backend.domains.user_features.inventory.engine.inventory_enricher import InventoryEnricher
from src.backend.domains.user_features.inventory.services.inventory_session_service import InventorySessionService
from src.shared.enums.inventory_enums import InventorySection, InventoryViewTarget
from src.shared.schemas.inventory import (
    BagContextDTO,
    DetailsContextDTO,
    DollContextDTO,
    InventoryUIPayloadDTO,
    PaginationDTO,
)


class InventoryService:
    """
    Сервис, реализующий бизнес-логику домена Инвентаря.
    """

    PAGE_SIZE = 9

    def __init__(
        self,
        session_service: InventorySessionService,
        enricher: InventoryEnricher,
        bridge: InventoryDispatcherBridge,
    ):
        self.session_service = session_service
        self.enricher = enricher
        self.bridge = bridge

    # --- Read Operations (Views) ---

    async def get_main_menu(self, char_id: int) -> InventoryUIPayloadDTO:
        """
        Возвращает данные для главного экрана (Кукла).
        """
        session = await self.session_service.get_session(char_id)

        equipped_items = {}
        for slot, item_id in session.equipped.items():
            if item_id in session.items:
                equipped_items[slot] = session.items[item_id]

        wallet_view = self.enricher.enrich_wallet(session.wallet)

        context = DollContextDTO(
            equipped_items=equipped_items,
            stats=session.stats.model_dump(),
            wallet=wallet_view,
        )

        return InventoryUIPayloadDTO(
            screen=InventoryViewTarget.MAIN,
            title=InventoryResources.TITLE_MAIN,
            context=context,
            navigation_buttons=InventoryResources.get_section_buttons(),
        )

    async def get_bag_view(self, char_id: int, section: str, category: str | None, page: int) -> InventoryUIPayloadDTO:
        """
        Возвращает данные для экрана сумки с фильтрацией и пагинацией.
        """
        session = await self.session_service.get_session(char_id)

        # Фильтрация
        all_items = [item for item in session.items.values() if item.location == "bag"]

        if section and section != "all":
            all_items = [item for item in all_items if item.item_type == section]  # Упрощенный фильтр

        # Пагинация
        total_items = len(all_items)
        total_pages = ceil(total_items / self.PAGE_SIZE)
        start = page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        items_on_page = all_items[start:end]

        pagination = PaginationDTO(
            page=page,
            total_pages=total_pages,
            has_next=(page < total_pages - 1),
            has_prev=(page > 0),
        )

        context = BagContextDTO(
            items=items_on_page,
            pagination=pagination,
            active_section=InventorySection(section),
            active_category=category,
            back_target=InventoryViewTarget.MAIN,
        )

        return InventoryUIPayloadDTO(
            screen=InventoryViewTarget.BAG,
            title=InventoryResources.SECTION_NAMES.get(section, InventoryResources.TITLE_BAG),
            context=context,
            navigation_buttons=InventoryResources.get_filter_buttons(section, category),
        )

    async def get_item_details(self, char_id: int, item_id: int) -> InventoryUIPayloadDTO:
        """
        Возвращает детальную информацию о предмете.
        """
        session = await self.session_service.get_session(char_id)

        item = session.items.get(item_id)
        if not item:
            # TODO: Handle item not found
            raise ValueError("Item not found")

        # Сравнение с надетым
        comparison_item = None
        if item.equipped_slot:
            equipped_id = session.equipped.get(item.equipped_slot)
            if equipped_id and equipped_id != item_id:
                comparison_item = session.items.get(equipped_id)

        context = DetailsContextDTO(
            item=item,
            comparison_item=comparison_item,
            actions=InventoryResources.get_item_actions(item_id, item.location == "equipped", item.item_type),
            back_target=InventoryViewTarget.BAG,  # TODO: smarter back target
        )

        return InventoryUIPayloadDTO(
            screen=InventoryViewTarget.DETAILS,
            title=item.data.name,
            context=context,
        )

    # --- Write Operations (Actions) ---

    async def equip_item(self, char_id: int, item_id: int, slot: str | None = None) -> InventoryUIPayloadDTO:
        """
        Надевает предмет на персонажа.
        """
        session = await self.session_service.get_session(char_id)

        item_to_equip = session.items.get(item_id)
        if not item_to_equip or item_to_equip.location != "bag":
            raise ValueError("Item not in bag")

        # Проверка типа данных перед доступом к valid_slots
        # item_to_equip.data - это Union. Не у всех типов есть valid_slots.
        valid_slots = getattr(item_to_equip.data, "valid_slots", [])
        if not valid_slots:
            raise ValueError("Item cannot be equipped")

        target_slot = slot or valid_slots[0]

        # Если в слоте уже что-то есть, снимаем
        if target_slot in session.equipped:
            item_to_unequip_id = session.equipped[target_slot]
            if item_to_unequip_id in session.items:
                session.items[item_to_unequip_id].location = "bag"
                session.items[item_to_unequip_id].equipped_slot = None

        # Надеваем новый предмет
        item_to_equip.location = "equipped"
        item_to_equip.equipped_slot = target_slot
        session.equipped[target_slot] = item_id

        session.is_dirty = True
        await self.session_service.save_session(session)

        # Возвращаем обновленный главный экран
        return await self.get_main_menu(char_id)

    async def unequip_item(self, char_id: int, item_id: int) -> InventoryUIPayloadDTO:
        """
        Снимает предмет с персонажа.
        """
        session = await self.session_service.get_session(char_id)

        item_to_unequip = session.items.get(item_id)
        if not item_to_unequip or item_to_unequip.location != "equipped":
            raise ValueError("Item not equipped")

        slot = item_to_unequip.equipped_slot
        if slot and session.equipped.get(slot) == item_id:
            del session.equipped[slot]

        item_to_unequip.location = "bag"
        item_to_unequip.equipped_slot = None

        session.is_dirty = True
        await self.session_service.save_session(session)

        return await self.get_main_menu(char_id)

    async def drop_item(self, char_id: int, item_id: int) -> InventoryUIPayloadDTO:
        """
        Удаляет предмет из инвентаря.
        """
        session = await self.session_service.get_session(char_id)

        if item_id not in session.items:
            raise ValueError("Item not found")

        # Если предмет надет, снимаем его
        if session.items[item_id].location == "equipped":
            slot = session.items[item_id].equipped_slot
            if slot and session.equipped.get(slot) == item_id:
                del session.equipped[slot]

        del session.items[item_id]

        session.is_dirty = True
        await self.session_service.save_session(session)

        # Возвращаем сумку
        return await self.get_bag_view(char_id, "all", None, 0)
