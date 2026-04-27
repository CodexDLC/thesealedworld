from typing import Any

from pydantic import computed_field

from src.backend.domains.internal_systems.context_assembler.schemas.base import BaseTempContext
from src.shared.schemas.inventory import InventoryStatsDTO, WalletDTO


class InventoryTempContext(BaseTempContext):
    """
    Контекст для сборки сессии инвентаря.
    Преобразует сырые данные из БД в структуру InventorySessionDTO.
    """

    @computed_field
    def char_id(self) -> int:
        return self.core_meta.character_id if self.core_meta else 0

    @computed_field
    def items(self) -> dict[int, Any]:
        """
        Все предметы (Сумка + Экипировка).
        Key: inventory_id
        Value: InventoryItemDTO (dict)
        """
        if not self.core_inventory:
            return {}

        items_map = {}
        for item in self.core_inventory:
            # item может быть dict или DTO
            item_data = item.model_dump() if hasattr(item, "model_dump") else item
            inv_id = item_data.get("inventory_id")
            if inv_id:
                items_map[inv_id] = item_data
        return items_map

    @computed_field
    def equipped(self) -> dict[str, int]:
        """
        Только ссылки на надетые предметы.
        Key: slot_name
        Value: inventory_id
        """
        if not self.core_inventory:
            return {}

        equipped_map = {}
        for item in self.core_inventory:
            item_data = item.model_dump() if hasattr(item, "model_dump") else item

            # Проверяем, что предмет надет и имеет слот
            if item_data.get("location") == "equipped" and item_data.get("equipped_slot"):
                slot = item_data["equipped_slot"]
                inv_id = item_data.get("inventory_id")
                if slot and inv_id:
                    equipped_map[slot] = inv_id
        return equipped_map

    @computed_field
    def wallet(self) -> WalletDTO:
        """
        Кошелек.
        """
        if not self.core_wallet:
            return WalletDTO()

        return WalletDTO(
            currency=self.core_wallet.get("currency", {}),
            resources=self.core_wallet.get("resources", {}),
            components=self.core_wallet.get("components", {}),
        )

    @computed_field
    def stats(self) -> InventoryStatsDTO:
        """
        Базовые статы инвентаря (вес, слоты).
        """
        # TODO: Рассчитать реальный вес на основе items
        current_weight = 0.0
        slots_used = 0

        if self.core_inventory:
            slots_used = len(self.core_inventory)
            # Пример расчета веса (если бы у нас были данные о весе в item.data)
            # for item in self.core_inventory:
            #     item_data = ...
            #     current_weight += item_data.get("weight", 0) * item_data.get("quantity", 1)

        return InventoryStatsDTO(
            current_weight=current_weight,
            slots_used=slots_used,
            # max_weight и slots_total берутся дефолтные или из атрибутов (если переданы)
        )
