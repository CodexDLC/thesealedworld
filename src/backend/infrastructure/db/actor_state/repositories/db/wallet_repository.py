from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.infrastructure.db.actor_state.models import ResourceWallet


class WalletRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_wallet(self, char_id: int) -> ResourceWallet | None:
        log.debug(f"WalletRepository | action=get_wallet char_id={char_id}")
        stmt = select(ResourceWallet).where(ResourceWallet.character_id == char_id)
        try:
            result = await self.session.scalars(stmt)
            return result.one_or_none()
        except SQLAlchemyError as exc:
            log.exception(f"WalletRepository | action=get_wallet status=failed char_id={char_id} error={exc}")
            raise


WalletRepoORM = WalletRepository
