from typing import Protocol

from fastapi import Request


class PermissionProvider(Protocol):
    async def can(self, request: Request, permission: str) -> bool: ...


class AllowAllPermissionProvider:
    async def can(self, request: Request, permission: str) -> bool:
        return True
