from backend.core.config import settings


def test_app_name() -> None:
    """Verifies that the default app name loads correctly."""
    assert settings.app_name == "Hermes AI Research Assistant"


def test_database_url() -> None:
    """Verifies that database URLs are constructed correctly."""
    url = settings.db.url
    async_url = settings.db.async_url
    assert "postgresql://" in url
    assert "postgresql+asyncpg://" in async_url
