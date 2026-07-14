import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from backend.core.config import settings

logger = logging.getLogger(__name__)


def setup_telemetry(service_name: str) -> None:
    """Configures the TracerProvider and OTLP exporter to send spans to Jaeger."""
    # Check if a TracerProvider is already set (non-proxy) to avoid reload error
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        logger.info(
            f"OpenTelemetry tracing is already configured for: {service_name}"
        )
        return

    # 1. Define resources
    resource = Resource.create(attributes={"service.name": service_name})
    provider = TracerProvider(resource=resource)

    # 2. Add OTLP grpc span processor pointing to Jaeger
    endpoint = settings.monitoring.exporter_otlp_endpoint
    try:
        # grpc OTLPSpanExporter
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        logger.info(
            f"OpenTelemetry tracing initialized for service: {service_name} "
            f"exporting to: {endpoint}"
        )
    except Exception as e:
        logger.warning(
            f"Failed to initialize OTLP gRPC Span Exporter to {endpoint}: {e}. "
            "Tracing is disabled."
        )


def setup_fastapi_instrumentation(app: FastAPI) -> None:
    """Instruments FastAPI application endpoints."""
    try:
        FastAPIInstrumentor().instrument_app(app)
        logger.info("FastAPI application instrumented with OpenTelemetry.")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI application: {e}")


def setup_celery_instrumentation() -> None:
    """Instruments Celery workers with OpenTelemetry."""
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()  # type: ignore[no-untyped-call]
        logger.info("Celery tasks instrumented with OpenTelemetry.")
    except Exception as e:
        logger.warning(f"Failed to instrument Celery: {e}")
