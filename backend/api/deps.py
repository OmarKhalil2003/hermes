from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import decode_token
from backend.models.auth import Permission, Role, User, role_permissions, user_roles
from backend.repositories.auth import UserRepository

# OAuth2 Password Bearer flow scheme pointing to our login route
reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    """Decodes JWT and retrieves the authenticated user from the database.

    Args:
        db: Async database session.
        token: The OAuth2 bearer token.

    Returns:
        User: The authenticated user instance.

    Raises:
        HTTPException: 401 Unauthorized if token is invalid or user doesn't exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id_str: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id_str is None or token_type != "access":
            raise credentials_exception
        user_id = UUID(user_id_str)
    except (JWTError, ValueError) as e:
        raise credentials_exception from e

    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensures that the authenticated user account is active.

    Args:
        current_user: The user fetched from the token.

    Returns:
        User: The active user.

    Raises:
        HTTPException: 400 Bad Request if user account is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


def check_permissions(permission_name: str) -> Any:
    """RBAC dependency guard checking if the user has the required permission.

    Superusers automatically bypass this guard.

    Args:
        permission_name: The name of the required permission (e.g. "document:upload").

    Returns:
        Callable: A dependency function for FastAPI route guards.
    """

    async def permission_dependency(
        current_user: User = Depends(get_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        # Query to verify if the user possesses the permission via their roles
        stmt = (
            select(Permission)
            .join(role_permissions)
            .join(Role)
            .join(user_roles)
            .where(user_roles.c.user_id == current_user.id)
            .where(Permission.name == permission_name)
        )
        result = await db.execute(stmt)
        permission = result.scalars().first()

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return permission_dependency
