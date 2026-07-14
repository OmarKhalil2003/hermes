import logging

from sqlalchemy import select

from backend.core.config import settings
from backend.core.database import async_session_factory
from backend.models.jobs import TrainingJob

logger = logging.getLogger(__name__)

# Thread-safe in-memory cache for active model/adapter routing
_ACTIVE_ADAPTER: str | None = None


def get_active_adapter() -> str:
    """Returns the current active model or adapter path/name.

    Falls back to settings.models.llm_model if no custom adapter is active.
    """
    global _ACTIVE_ADAPTER
    if _ACTIVE_ADAPTER is None:
        return settings.models.llm_model
    return _ACTIVE_ADAPTER


def set_active_adapter(adapter_name: str | None) -> None:
    """Updates the runtime active adapter target."""
    global _ACTIVE_ADAPTER
    if adapter_name in [None, "base", "default", settings.models.llm_model]:
        _ACTIVE_ADAPTER = None
    else:
        _ACTIVE_ADAPTER = adapter_name
    logger.info(f"Runtime active adapter updated to: {get_active_adapter()}")


async def init_active_adapter() -> None:
    """Loads the active adapter from database upon application start."""
    try:
        async with async_session_factory() as session:
            stmt = select(TrainingJob).where(
                TrainingJob.is_active, TrainingJob.status == "completed"
            )
            result = await session.execute(stmt)
            active_job = result.scalars().first()
            if active_job:
                set_active_adapter(active_job.model_name)
            else:
                set_active_adapter(None)
    except Exception as e:
        logger.error(f"Failed to initialize active adapter from database: {e}")
        set_active_adapter(None)
