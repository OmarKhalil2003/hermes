import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from backend.api.deps import check_permissions
from backend.api.v1.router import api_router
from backend.core.config import settings
from backend.core.logging import logger, request_id_var, trace_id_var
from backend.core.metrics import PrometheusMetricsMiddleware
from backend.core.telemetry import setup_fastapi_instrumentation, setup_telemetry
from backend.models.auth import User
from backend.schemas.auth import UserOut
from backend.services.deployment import init_active_adapter


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    setup_telemetry("hermes-backend")
    await init_active_adapter()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(PrometheusMetricsMiddleware)
setup_fastapi_instrumentation(app)

app.include_router(api_router, prefix="/api/v1")


@app.get("/api/v1/protected", response_model=UserOut)
async def protected_route(
    current_user: User = Depends(check_permissions("document:upload")),
) -> Any:
    """A test endpoint protected by custom RBAC permission checks."""
    return current_user


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next: Any) -> Response:
    """Middleware to track request/trace identifiers and log execution time."""
    start_time = time.perf_counter()

    # Extract trace headers or generate fallback
    req_id = request.headers.get("X-Request-ID", f"req-{int(start_time * 1000)}")
    trace_id = request.headers.get("X-Trace-ID", f"trace-{int(start_time * 1000)}")

    # Bind to ContextVar
    request_id_var.set(req_id)
    trace_id_var.set(trace_id)

    response: Response = await call_next(request)

    # Log execution stats
    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        f"HTTP {request.method} {request.url.path} responded {response.status_code}",
        extra={"execution_time": round(duration_ms, 2)},
    )

    # Propagate headers
    response.headers["X-Request-ID"] = req_id or ""
    response.headers["X-Trace-ID"] = trace_id or ""
    return response


@app.get("/healthz")
async def health_check() -> dict[str, str]:
    """Health check endpoint to verify system status."""
    return {"status": "healthy", "timestamp": str(time.time())}


@app.get("/metrics")
async def metrics_endpoint() -> Response:
    """Exports Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
