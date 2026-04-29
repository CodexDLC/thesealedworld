from typing import Any, TypeVar, overload

import httpx
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)  # For automatic parsing into Pydantic models


class BaseApiClient:
    """
    Base API Client for the Frontend/Gateway.
    Uses a long-lived httpx.AsyncClient for efficiency.
    """

    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self.client = client
        self.base_url = base_url.rstrip("/")

    @overload
    async def _request(
        self,
        method: str,
        endpoint: str,
        response_model: type[T],
        **kwargs: Any,
    ) -> T: ...

    @overload
    async def _request(
        self,
        method: str,
        endpoint: str,
        response_model: None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None: ...

    async def _request(
        self,
        method: str,
        endpoint: str,
        response_model: type[T] | None = None,
        **kwargs: Any,
    ) -> T | dict[str, Any] | None:
        """
        Internal helper for making requests and validating responses.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = await self.client.request(method, url, **kwargs)
        response.raise_for_status()
        if response.status_code == 204 or not response.content:
            return None

        if response_model:
            return response_model.model_validate(response.json())
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}
