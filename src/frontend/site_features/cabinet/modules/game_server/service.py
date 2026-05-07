from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True)
class GameServerSnapshot:
    service_name: str
    status: str
    checks: tuple[str, ...]


class GameServerCabinetService:
    async def get_snapshot(self, request: Request) -> GameServerSnapshot:
        app_title = getattr(request.app, "title", "Frontend")
        return GameServerSnapshot(
            service_name=app_title,
            status="online",
            checks=("frontend_app", "cabinet_engine"),
        )
