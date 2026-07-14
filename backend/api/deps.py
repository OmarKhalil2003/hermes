from typing import Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.auth import User

__all__ = [
    "check_permissions",
    "get_active_user",
    "get_current_user",
    "get_db",
]


# Bypass tokens, always return default admin user
async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """Retrieves or creates a default admin superuser bypassing JWT token checks."""
    stmt = select(User).where(User.email == "admin@hermes.ai")
    res = await db.execute(stmt)
    user = res.scalars().first()
    if user:
        return user

    # Fallback to any user
    stmt = select(User)
    res = await db.execute(stmt)
    user = res.scalars().first()
    if user:
        return user

    # Create default user on the fly if database is empty
    user = User(
        email="admin@hermes.ai",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Returns the authenticated default active user."""
    return current_user


def check_permissions(_permission_name: str) -> Any:
    """Bypasses all permission checks by returning the default user."""

    async def permission_dependency(
        current_user: User = Depends(get_active_user),
    ) -> User:
        return current_user

    return permission_dependency
