import time
from typing import Any

from fastapi import Request, Response
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

# 1. Define custom Prometheus metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total count of HTTP requests handled by Hermes.",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latencies in seconds.",
    ["method", "endpoint"],
    buckets=(
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
        float("inf"),
    ),
)


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request duration and count metrics."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        method = request.method
        endpoint = request.url.path

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
            status = str(response.status_code)
            return response
        except Exception as e:
            status = "500"
            raise e
        finally:
            duration = time.perf_counter() - start_time
            # Record metrics
            HTTP_REQUESTS_TOTAL.labels(
                method=method, endpoint=endpoint, status=status
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method, endpoint=endpoint
            ).observe(duration)
