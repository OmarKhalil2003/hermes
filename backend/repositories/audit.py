from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit import AuditLog
from backend.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository implementation for AuditLog-specific queries."""

    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(AuditLog, db_session)

    async def get_logs_by_user_id(self, user_id: UUID) -> Sequence[AuditLog]:
        """Retrieves audit log entries recorded for a specific user.

        Args:
            user_id: The UUID of the user owner.

        Returns:
            Sequence[AuditLog]: List of audit log entries.
        """
        query = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
