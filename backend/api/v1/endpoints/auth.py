from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from backend.repositories.auth import SessionRepository, UserRepository
from backend.schemas.auth import Token, TokenRefreshRequest, UserCreate, UserOut

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)) -> Any:
    """Registers a new user account with hashed credentials.

    Args:
        user_in: Input user creation schema.
        db: Database session.

    Returns:
        UserOut: Public representation of created user.
    """
    user_repo = UserRepository(db)
    existing_user = await user_repo.get_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_pw = get_password_hash(user_in.password)
    user = await user_repo.create(
        {
            "email": user_in.email,
            "hashed_password": hashed_pw,
            "is_superuser": user_in.is_superuser,
            "is_active": True,
        }
    )
    # Commit changes
    await db.commit()
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Authenticates user credentials and issues OAuth2 access/refresh tokens.

    Also tracks the login session in the database.

    Args:
        form_data: Standard OAuth2 password form payload.
        db: Database session.

    Returns:
        Token: Token authentication payload.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )

    # Generate Access & Refresh Tokens
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    # Calculate refresh token expiration
    refresh_expiry = datetime.now(UTC).replace(tzinfo=None) + timedelta(
        days=settings.security.refresh_token_expire_days
    )

    # Store refresh session in database
    session_repo = SessionRepository(db)
    await session_repo.create(
        {
            "user_id": user.id,
            "token": refresh_token,
            "expires_at": refresh_expiry,
            "is_revoked": False,
        }
    )

    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh_token_route(
    payload_in: TokenRefreshRequest, db: AsyncSession = Depends(get_db)
) -> Any:
    """Uses a valid refresh token to obtain a new access token.

    Args:
        payload_in: Schema containing the refresh token string.
        db: Database session.

    Returns:
        Token: Fresh access token payload.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(payload_in.refresh_token)
        user_id_str: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id_str is None or token_type != "refresh":
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e

    # Validate active session in database
    session_repo = SessionRepository(db)
    db_session = await session_repo.get_by_token(payload_in.refresh_token)
    if (
        not db_session
        or db_session.is_revoked
        or db_session.expires_at < datetime.now(UTC).replace(tzinfo=None)
    ):
        raise credentials_exception

    # Create new tokens
    access_token = create_access_token(subject=db_session.user_id)
    new_refresh_token = create_refresh_token(subject=db_session.user_id)
    refresh_expiry = datetime.now(UTC).replace(tzinfo=None) + timedelta(
        days=settings.security.refresh_token_expire_days
    )

    # Revoke old session and store new one
    db_session.is_revoked = True
    await session_repo.update(db_session, db_session)

    await session_repo.create(
        {
            "user_id": db_session.user_id,
            "token": new_refresh_token,
            "expires_at": refresh_expiry,
            "is_revoked": False,
        }
    )

    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }
