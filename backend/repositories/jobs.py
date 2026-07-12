from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.jobs import Evaluation, TrainingJob
from backend.repositories.base import BaseRepository


class TrainingJobRepository(BaseRepository[TrainingJob]):
    """Repository implementation for TrainingJob database queries."""

    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(TrainingJob, db_session)

    async def get_jobs_by_status(self, status: str) -> Sequence[TrainingJob]:
        """Retrieves fine-tuning jobs filtered by status.

        Args:
            status: Status string (e.g. "running").

        Returns:
            Sequence[TrainingJob]: List of jobs matching the status.
        """
        query = select(TrainingJob).where(TrainingJob.status == status)
        result = await self.db_session.execute(query)
        return result.scalars().all()


class EvaluationRepository(BaseRepository[Evaluation]):
    """Repository implementation for Evaluation-specific database queries."""

    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(Evaluation, db_session)

    async def get_by_training_job_id(
        self, training_job_id: UUID
    ) -> Sequence[Evaluation]:
        """Retrieves evaluations linked to a specific fine-tuning training job.

        Args:
            training_job_id: The UUID of the training job.

        Returns:
            Sequence[Evaluation]: List of evaluations for the job.
        """
        query = select(Evaluation).where(Evaluation.training_job_id == training_job_id)
        result = await self.db_session.execute(query)
        return result.scalars().all()
