import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import bcrypt
from jose import jwt

# Fix passlib/bcrypt incompatibility in modern Python/bcrypt environments
if not hasattr(bcrypt, "__about__"):

    class DummyAbout:
        __version__ = getattr(bcrypt, "__version__", "unknown")

    bcrypt.__about__ = DummyAbout()  # type: ignore

orig_hashpw = bcrypt.hashpw


def patched_hashpw(password: bytes, salt: bytes) -> bytes:
    if len(password) > 72:
        password = password[:72]
    return orig_hashpw(password, salt)


bcrypt.hashpw = patched_hashpw

from passlib.context import CryptContext  # noqa: E402

from backend.core.config import settings  # noqa: E402

# Initialize password hashing context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against its hashed database version.

    Args:
        plain_password: The plaintext password.
        hashed_password: The bcrypt hashed password string.

    Returns:
        bool: True if password matches, False otherwise.
    """
    return bool(pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    """Generates a bcrypt hash of the provided password.

    Args:
        password: The plaintext password.

    Returns:
        str: The hashed password string.
    """
    return str(pwd_context.hash(password))


def create_access_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    """Generates an OAuth2 access token with a configurable expiration date.

    Args:
        subject: The token subject, typically the user's UUID or email.
        expires_delta: Optional timedelta for token expiration override.

    Returns:
        str: The encoded JWT token string.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.security.access_token_expire_minutes
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    return cast(
        str,
        jwt.encode(
            to_encode,
            settings.security.secret_key,
            algorithm=settings.security.algorithm,
        ),
    )


def create_refresh_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    """Generates a long-lived refresh token for authentication renewal.

    Args:
        subject: The token subject, typically the user's UUID or email.
        expires_delta: Optional timedelta for token expiration override.

    Returns:
        str: The encoded JWT refresh token string.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            days=settings.security.refresh_token_expire_days
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    return cast(
        str,
        jwt.encode(
            to_encode,
            settings.security.secret_key,
            algorithm=settings.security.algorithm,
        ),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decodes and validates a JWT token signature and expiration.

    Args:
        token: The encoded JWT token string.

    Returns:
        dict[str, Any]: The decoded token payload.

    Raises:
        JWTError: If signature verification or validation fails.
    """
    payload = jwt.decode(
        token,
        settings.security.secret_key,
        algorithms=[settings.security.algorithm],
    )
    return cast(dict[str, Any], payload)
