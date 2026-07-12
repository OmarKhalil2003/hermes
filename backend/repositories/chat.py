from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Conversation, Message
from backend.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository implementation for Conversation-specific database queries."""

    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(Conversation, db_session)

    async def get_by_user_id(self, user_id: UUID) -> Sequence[Conversation]:
        """Retrieves all conversation history threads for a user.

        Args:
            user_id: The UUID of the user owner.

        Returns:
            Sequence[Conversation]: List of conversation threads.
        """
        query = select(Conversation).where(Conversation.user_id == user_id)
        result = await self.db_session.execute(query)
        return result.scalars().all()


class MessageRepository(BaseRepository[Message]):
    """Repository implementation for Message-specific database queries."""

    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(Message, db_session)

    async def get_messages_by_conversation_id(
        self, conversation_id: UUID
    ) -> Sequence[Message]:
        """Retrieves all messages in a conversation ordered by creation time.

        Args:
            conversation_id: The UUID of the conversation thread.

        Returns:
            Sequence[Message]: Ordered list of conversation messages.
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()
