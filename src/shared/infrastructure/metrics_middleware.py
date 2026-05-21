"""Starlette middleware that records Prometheus HTTP metrics."""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.shared.infrastructure.metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS_IN_FLIGHT, HTTP_REQUESTS_TOTAL

_SKIP_PATHS = frozenset({"/metrics", "/health"})


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str = "unknown"):  # noqa: ANN001
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        path_template = self._path_template(request)
        method = request.method

        HTTP_REQUESTS_IN_FLIGHT.labels(service=self.service_name).inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
            HTTP_REQUESTS_TOTAL.labels(
                service=self.service_name,
                method=method,
                path_template=path_template,
                status=response.status_code,
            ).inc()
            HTTP_REQUEST_DURATION.labels(
                service=self.service_name,
                method=method,
                path_template=path_template,
            ).observe(time.perf_counter() - start)
            return response
        finally:
            HTTP_REQUESTS_IN_FLIGHT.labels(service=self.service_name).dec()

    @staticmethod
    def _path_template(request: Request) -> str:
        route = request.scope.get("route")
        if route and hasattr(route, "path"):
            return route.path
        return request.url.path
