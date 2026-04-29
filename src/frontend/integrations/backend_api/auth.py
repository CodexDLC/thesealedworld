import uuid
from datetime import datetime

from pydantic import BaseModel

from src.frontend.integrations.backend_api.base import BaseApiClient


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class BackendAuthApi(BaseApiClient):
    async def login(self, email: str, password: str) -> TokenResponse:
        return await self._request(
            "POST",
            "/auth/login",
            response_model=TokenResponse,
            data={"username": email, "password": password},
        )

    async def current_user(self, access_token: str) -> UserResponse:
        return await self._request(
            "GET",
            "/auth/me",
            response_model=UserResponse,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    async def register(self, email: str, password: str) -> UserResponse:
        return await self._request(
            "POST",
            "/auth/register",
            response_model=UserResponse,
            json={"email": email, "password": password},
        )

    async def logout(self, refresh_token: str) -> None:
        await self._request("POST", "/auth/logout", json={"refresh_token": refresh_token})
