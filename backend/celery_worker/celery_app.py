from celery import Celery

from backend.core.config import settings
from backend.core.telemetry import setup_celery_instrumentation, setup_telemetry

# Configure distributed tracing for Celery worker process
setup_telemetry("hermes-celery-worker")
setup_celery_instrumentation()

celery_app = Celery(
    "hermes_tasks",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Auto-discover tasks in this folder
celery_app.autodiscover_tasks(["backend.celery_worker"])
