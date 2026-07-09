from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DB_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")
    name: str = Field(default="research_assistant")

    @property
    def url(self) -> str:
        """Returns synchronous PostgreSQL URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def async_url(self) -> str:
        """Returns asynchronous PostgreSQL URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Redis configuration for caching and rate limiting."""

    model_config = SettingsConfigDict(
        env_prefix="REDIS_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)

    @property
    def url(self) -> str:
        """Returns Redis URL."""
        return f"redis://{self.host}:{self.port}/{self.db}"


class RabbitMQSettings(BaseSettings):
    """RabbitMQ configuration for event streaming/brokerage."""

    model_config = SettingsConfigDict(
        env_prefix="RABBITMQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="localhost")
    port: int = Field(default=5672)
    user: str = Field(default="guest")
    password: str = Field(default="guest")

    @property
    def url(self) -> str:
        """Returns RabbitMQ connection URL."""
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}//"


class CelerySettings(BaseSettings):
    """Celery configuration for asynchronous task queuing."""

    model_config = SettingsConfigDict(
        env_prefix="CELERY_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    broker_url: str = Field(default="redis://localhost:6379/1")
    result_backend: str = Field(default="redis://localhost:6379/1")


class QdrantSettings(BaseSettings):
    """Qdrant Vector Database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="QDRANT_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    host: str = Field(default="localhost")
    port: int = Field(default=6333)
    grpc_port: int = Field(default=6334)
    api_key: str | None = Field(default=None)


class MLflowSettings(BaseSettings):
    """MLflow tracking server configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MLFLOW_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    tracking_uri: str = Field(default="http://localhost:5000")
    experiment_name: str = Field(default="research_assistant_evaluation")


class SecuritySettings(BaseSettings):
    """Authentication and encryption configurations."""

    model_config = SettingsConfigDict(
        env_prefix="JWT_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    secret_key: str = Field(default="CHANGE_THIS_IN_PRODUCTION_SECRET_KEY_1234567890")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)
    refresh_token_expire_days: int = Field(default=7)


class ModelSettings(BaseSettings):
    """LLM API configurations."""

    model_config = SettingsConfigDict(
        env_prefix="MODEL_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # API Keys & Endpoints
    openai_api_key: str | None = Field(default=None)
    openai_api_base: str | None = Field(default=None)

    # Models to use
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    reranker_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    llm_model: str = Field(default="gpt-4o-mini")

    # Fine-tuned adapter base models
    base_model_path: str = Field(default="Qwen/Qwen2.5-3B-Instruct")


class Settings(BaseSettings):
    """Global application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # General
    app_name: str = Field(default="Enterprise AI Research Assistant")
    environment: Literal["development", "production", "testing"] = Field(
        default="development"
    )
    debug: bool = Field(default=True)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # Sub-configs
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    mlflow: MLflowSettings = Field(default_factory=MLflowSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    models: ModelSettings = Field(default_factory=ModelSettings)


# Global settings singleton
settings = Settings()
