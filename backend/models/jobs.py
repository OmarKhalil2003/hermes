from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.auth import User


class TrainingJob(Base, TimestampMixin):
    """Fine-tuning job definition and current status tracking."""

    __tablename__ = "training_jobs"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(nullable=False)
    base_model: Mapped[str] = mapped_column(nullable=False)
    dataset_path: Mapped[str] = mapped_column(nullable=False)
    hyperparameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(default="pending", nullable=False)
    mlflow_run_id: Mapped[str | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="training_jobs")
    evaluations: Mapped[list[Evaluation]] = relationship(
        back_populates="training_job", cascade="all, delete-orphan"
    )


class Evaluation(Base, TimestampMixin):
    """Evaluation result for a specific model run."""

    __tablename__ = "evaluations"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    training_job_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("training_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_name: Mapped[str] = mapped_column(nullable=False)
    dataset_name: Mapped[str] = mapped_column(nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Relationships
    training_job: Mapped[TrainingJob | None] = relationship(
        back_populates="evaluations"
    )
