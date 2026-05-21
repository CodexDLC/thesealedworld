"""Prometheus metrics registry shared across all HTTP services."""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

REGISTRY = CollectorRegistry()

# ── HTTP metrics ──

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["service", "method", "path_template", "status"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["service", "method", "path_template"],
    registry=REGISTRY,
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

HTTP_REQUESTS_IN_FLIGHT = Gauge(
    "http_requests_in_flight",
    "HTTP requests currently being processed",
    ["service"],
    registry=REGISTRY,
)

# ── Event bus metrics ──

EVENT_PUBLISHED_TOTAL = Counter(
    "event_published_total",
    "Events published to Redis Streams",
    ["service", "event_type"],
    registry=REGISTRY,
)
