from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.document import Chunk, Document
from backend.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository implementation for Document-specific database queries."""

    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(Document, db_session)

    async def get_by_user_id(self, user_id: UUID) -> Sequence[Document]:
        """Retrieves all documents uploaded by a specific user.

        Args:
            user_id: The UUID of the user owner.

        Returns:
            Sequence[Document]: List of documents belonging to the user.
        """
        query = select(Document).where(Document.user_id == user_id)
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def get_by_checksum(self, checksum: str) -> Document | None:
        """Retrieves a document with the matching SHA-256 checksum.

        Args:
            checksum: The pre-calculated SHA-256 file checksum.

        Returns:
            Document | None: The document if found, else None.
        """
        query = select(Document).where(Document.checksum == checksum)
        result = await self.db_session.execute(query)
        return result.scalars().first()


class ChunkRepository(BaseRepository[Chunk]):
    """Repository implementation for Chunk-specific database queries."""

    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(Chunk, db_session)

    async def get_chunks_by_document_id(self, document_id: UUID) -> Sequence[Chunk]:
        """Retrieves all chunks parsed from a specific document ordered by index.

        Args:
            document_id: The UUID of the source document.

        Returns:
            Sequence[Chunk]: Ordered list of document chunks.
        """
        query = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.index.asc())
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
