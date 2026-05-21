from typing import Any, TypeVar, overload

import httpx
from loguru import logger
from pydantic import BaseModel, TypeAdapter

from src.frontend.config.settings import settings

T = TypeVar("T", bound=BaseModel)  # For automatic parsing into Pydantic models


class BaseApiClient:
    """
    Base API Client for the Frontend/Gateway.
    Uses a long-lived httpx.AsyncClient for efficiency.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        *,
        internal_service_key: str | None = None,
        internal_service_header: str | None = None,
    ):
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.internal_service_key = (
            internal_service_key if internal_service_key is not None else settings.backend_internal_service_key
        )
        self.internal_service_header = internal_service_header or settings.backend_internal_service_header

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
        kwargs["headers"] = self._headers(kwargs.get("headers"))
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.bind(
                method=method,
                endpoint=endpoint,
                status_code=exc.response.status_code,
                detail=_response_detail(exc.response),
            ).warning("BackendRequestRejected")
            raise
        except httpx.RequestError as exc:
            logger.bind(method=method, endpoint=endpoint, error=str(exc)).warning("BackendRequestUnavailable")
            raise

        logger.bind(method=method, endpoint=endpoint, status_code=response.status_code).debug("BackendRequestCompleted")
        if response.status_code == 204 or not response.content:
            return None

        if response_model:
            data = response.json()
            if hasattr(response_model, "model_validate"):
                return response_model.model_validate(data)
            return TypeAdapter(response_model).validate_python(data)
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}

    def _headers(self, headers: Any) -> dict[str, str]:
        merged = dict(headers or {})
        if self.internal_service_key:
            merged.setdefault(self.internal_service_header, self.internal_service_key)
        return merged


def _response_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text
    if isinstance(data, dict):
        return str(data.get("detail") or data)
    return str(data)
