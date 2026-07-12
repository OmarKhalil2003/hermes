from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.auth import Permission, Role, Session, User
from backend.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository implementation for User-specific database queries."""

    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(User, db_session)

    async def get_by_email(self, email: str) -> User | None:
        """Retrieves a user by their email address.

        Args:
            email: The email address to look up.

        Returns:
            User | None: The found User instance or None.
        """
        query = select(User).where(User.email == email)
        result = await self.db_session.execute(query)
        return result.scalars().first()


class RoleRepository(BaseRepository[Role]):
    """Repository implementation for Role-specific database queries."""

    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(Role, db_session)

    async def get_by_name(self, name: str) -> Role | None:
        """Retrieves a role by its name identifier.

        Args:
            name: The role name (e.g., "admin").

        Returns:
            Role | None: The found Role instance or None.
        """
        query = select(Role).where(Role.name == name)
        result = await self.db_session.execute(query)
        return result.scalars().first()


class PermissionRepository(BaseRepository[Permission]):
    """Repository implementation for Permission-specific database queries."""

    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(Permission, db_session)

    async def get_by_name(self, name: str) -> Permission | None:
        """Retrieves a permission by its name identifier.

        Args:
            name: The permission name (e.g., "document:upload").

        Returns:
            Permission | None: The found Permission instance or None.
        """
        query = select(Permission).where(Permission.name == name)
        result = await self.db_session.execute(query)
        return result.scalars().first()


class SessionRepository(BaseRepository[Session]):
    """Repository implementation for Session-specific database queries."""

    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(Session, db_session)

    async def get_by_token(self, token: str) -> Session | None:
        """Retrieves an active session by token string.

        Args:
            token: The token to search for.

        Returns:
            Session | None: The found Session instance or None.
        """
        query = select(Session).where(Session.token == token)
        result = await self.db_session.execute(query)
        return result.scalars().first()
