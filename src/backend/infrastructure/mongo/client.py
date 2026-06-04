from typing import Any

from src.backend.config.settings import settings


class MongoClientProvider:
    """Lazy async MongoDB client provider shared by backend infrastructure."""

    def __init__(
        self,
        *,
        url: str | None = None,
        database_name: str | None = None,
        server_selection_timeout_ms: int | None = None,
    ) -> None:
        self.url = url or settings.mongo_url
        self.database_name = database_name or settings.mongo_database
        self.server_selection_timeout_ms = (
            server_selection_timeout_ms
            if server_selection_timeout_ms is not None
            else settings.mongo_server_selection_timeout_ms
        )
        self._client: Any | None = None

    def client(self) -> Any:
        if self._client is None:
            from pymongo import AsyncMongoClient

            self._client = AsyncMongoClient(
                self.url,
                serverSelectionTimeoutMS=self.server_selection_timeout_ms,
            )
        return self._client

    def database(self) -> Any:
        return self.client()[self.database_name]

    async def ping(self) -> None:
        await self.client().admin.command("ping")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


_provider = MongoClientProvider()


def get_mongo_provider() -> MongoClientProvider:
    return _provider
