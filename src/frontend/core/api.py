from typing import Any, TypeVar, overload

import httpx
from loguru import logger
from pydantic import BaseModel, TypeAdapter

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
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Backend request rejected: method={} endpoint={} status={} detail={}",
                method,
                endpoint,
                exc.response.status_code,
                _response_detail(exc.response),
            )
            raise
        except httpx.RequestError:
            logger.opt(exception=True).critical("Backend request failed: method={} endpoint={}", method, endpoint)
            raise

        logger.info(
            "Backend request completed: method={} endpoint={} status={}", method, endpoint, response.status_code
        )
        if response.status_code == 204 or not response.content:
            return None

        if response_model:
            data = response.json()
            if hasattr(response_model, "model_validate"):
                return response_model.model_validate(data)
            return TypeAdapter(response_model).validate_python(data)
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}


def _response_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text
    if isinstance(data, dict):
        return str(data.get("detail") or data)
    return str(data)
