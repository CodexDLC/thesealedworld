from typing import Literal

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.backend.database.db_contract.i_wallet_repo import IWalletRepo
from src.backend.database.postgres.models.inventory import ResourceWallet


class WalletRepoORM(IWalletRepo):
    """
    Реализация IWalletRepo с использованием SQLAlchemy ORM.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        log.debug(f"WalletRepoORM | status=initialized session={session}")

    async def ensure_wallet_exists(self, char_id: int) -> None:
        """
        Проверяет существование кошелька и создает его, если он отсутствует.

        Args:
            char_id: ID персонажа.
        """
        try:
            wallet = await self.session.get(ResourceWallet, char_id)
            if not wallet:
                new_wallet = ResourceWallet(character_id=char_id)
                self.session.add(new_wallet)
                await self.session.flush()
                log.info(f"WalletRepoORM | action=create_wallet status=success char_id={char_id}")
        except SQLAlchemyError as e:
            log.exception(f"WalletRepoORM | action=ensure_wallet_exists status=failed char_id={char_id} error={e}")
            raise

    async def get_wallet(self, char_id: int) -> ResourceWallet:
        """
        Получает кошелек персонажа.

        Args:
            char_id: ID персонажа.

        Returns:
            ResourceWallet: Объект кошелька.
        """
        await self.ensure_wallet_exists(char_id)
        try:
            result = await self.session.execute(select(ResourceWallet).where(ResourceWallet.character_id == char_id))
            return result.scalar_one()
        except SQLAlchemyError as e:
            log.exception(f"WalletRepoORM | action=get_wallet status=failed char_id={char_id} error={e}")
            raise

    async def get_resource_amount(
        self,
        char_id: int,
        group: Literal["currency", "resources", "components"],
        key: str,
    ) -> int:
        """
        Получает количество ресурса в кошельке.

        Args:
            char_id: ID персонажа.
            group: Группа ресурсов (currency, resources, components).
            key: Ключ ресурса.

        Returns:
            int: Количество ресурса.
        """
        wallet = await self.get_wallet(char_id)
        target_dict: dict = getattr(wallet, group)
        return target_dict.get(key, 0)

    async def add_resource(
        self,
        char_id: int,
        group: Literal["currency", "resources", "components"],
        key: str,
        amount: int,
    ) -> None:
        """
        Добавляет ресурс в кошелек.

        Args:
            char_id: ID персонажа.
            group: Группа ресурсов.
            key: Ключ ресурса.
            amount: Количество для добавления.
        """
        wallet = await self.get_wallet(char_id)
        target_dict: dict = getattr(wallet, group)

        current_amount = target_dict.get(key, 0)
        target_dict[key] = current_amount + amount

        flag_modified(wallet, group)
        log.debug(f"WalletRepoORM | action=add_resource char_id={char_id} group='{group}' key='{key}' amount={amount}")

    async def remove_resource(
        self,
        char_id: int,
        group: Literal["currency", "resources", "components"],
        key: str,
        amount: int,
    ) -> bool:
        """
        Удаляет ресурс из кошелька.

        Args:
            char_id: ID персонажа.
            group: Группа ресурсов.
            key: Ключ ресурса.
            amount: Количество для удаления.

        Returns:
            bool: True, если ресурс успешно удален, False, если недостаточно средств.
        """
        wallet = await self.get_wallet(char_id)
        target_dict: dict = getattr(wallet, group)

        current_amount = target_dict.get(key, 0)
        if current_amount < amount:
            log.warning(
                f"WalletRepo | Insufficient resources for {char_id}: "
                f"has {current_amount} of {key}, but {amount} is required."
            )
            return False

        target_dict[key] = current_amount - amount
        if target_dict[key] == 0:
            del target_dict[key]

        flag_modified(wallet, group)
        log.debug(
            f"WalletRepoORM | action=remove_resource char_id={char_id} group='{group}' key='{key}' amount={amount}"
        )
        return True

    async def update_wallet(
        self, char_id: int, currency: dict[str, int], resources: dict[str, int], components: dict[str, int]
    ) -> None:
        """
        Полностью обновляет содержимое кошелька.

        Args:
            char_id: ID персонажа.
            currency: Словарь валют.
            resources: Словарь ресурсов.
            components: Словарь компонентов.
        """
        wallet = await self.get_wallet(char_id)

        wallet.currency = currency
        wallet.resources = resources
        wallet.components = components

        flag_modified(wallet, "currency")
        flag_modified(wallet, "resources")
        flag_modified(wallet, "components")

        log.debug(f"WalletRepoORM | action=update_wallet char_id={char_id}")
