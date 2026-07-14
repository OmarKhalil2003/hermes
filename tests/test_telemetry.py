import pytest
from httpx import AsyncClient
from opentelemetry import trace
from prometheus_client import REGISTRY

from backend.core.telemetry import setup_telemetry


def test_setup_telemetry_registers_provider() -> None:
    """Verifies setup_telemetry initializes global trace provider."""
    # Run setup
    setup_telemetry("hermes-test-service")

    # Fetch provider
    provider = trace.get_tracer_provider()
    assert provider is not None


@pytest.mark.asyncio
async def test_prometheus_metrics_middleware(client: AsyncClient) -> None:
    """Verifies HTTP requests update Prometheus metrics via middleware."""
    # Get current sample counts
    initial_requests = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "endpoint": "/healthz", "status": "200"},
    )
    if initial_requests is None:
        initial_requests = 0.0

    # Call /healthz endpoint
    response = await client.get("/healthz")
    assert response.status_code == 200

    # Verify metric incremented
    new_requests = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "endpoint": "/healthz", "status": "200"},
    )
    assert new_requests is not None
    assert new_requests == initial_requests + 1.0


@pytest.mark.asyncio
async def test_metrics_endpoint_exports_values(client: AsyncClient) -> None:
    """Verifies the /metrics endpoint outputs prometheus formatted metrics."""
    # Perform a request to ensure stats exist
    await client.get("/healthz")

    # Get /metrics
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds_bucket" in response.text
