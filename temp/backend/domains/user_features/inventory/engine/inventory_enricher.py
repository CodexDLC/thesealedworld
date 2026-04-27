from src.backend.resources.game_data.items.raw_resources import RAW_RESOURCES_DB
from src.backend.resources.game_data.items.schemas import ResourceDTO
from src.shared.schemas.inventory import EnrichedCurrencyDTO, WalletDTO, WalletViewDTO


class InventoryEnricher:
    """
    Обогащает "сырые" DTO из сессии данными из статических баз (в памяти).
    Например, добавляет названия к ID валют.
    """

    def __init__(self):
        # Создаем плоский индекс для быстрого поиска
        self._flat_db: dict[str, ResourceDTO] = {}
        for category in RAW_RESOURCES_DB.values():
            self._flat_db.update(category)  # type: ignore

    def enrich_wallet(self, wallet: WalletDTO) -> WalletViewDTO:
        """
        Преобразует WalletDTO (dict) в WalletViewDTO (list of objects with names).
        """

        enriched_currency = []
        for currency_id, amount in wallet.currency.items():
            resource_data = self._flat_db.get(currency_id)
            name = resource_data.name_ru if resource_data else currency_id.capitalize()
            enriched_currency.append(EnrichedCurrencyDTO(id=currency_id, name=name, amount=amount))

        enriched_resources = []
        for resource_id, amount in wallet.resources.items():
            resource_data = self._flat_db.get(resource_id)
            name = resource_data.name_ru if resource_data else resource_id.capitalize()
            enriched_resources.append(EnrichedCurrencyDTO(id=resource_id, name=name, amount=amount))

        enriched_components = []
        for component_id, amount in wallet.components.items():
            resource_data = self._flat_db.get(component_id)
            name = resource_data.name_ru if resource_data else component_id.capitalize()
            enriched_components.append(EnrichedCurrencyDTO(id=component_id, name=name, amount=amount))

        return WalletViewDTO(
            currency=enriched_currency,
            resources=enriched_resources,
            components=enriched_components,
        )
