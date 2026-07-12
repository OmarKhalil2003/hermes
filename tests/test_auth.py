from collections.abc import AsyncGenerator
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.core.security import create_refresh_token
from backend.main import app
from backend.models.auth import Role
from backend.repositories.auth import (
    PermissionRepository,
    RoleRepository,
    UserRepository,
)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Test client fixture that overrides get_db dependency."""

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_user_registration(client: AsyncClient) -> None:
    # Test valid registration
    reg_data = {
        "email": "register@example.com",
        "password": "strongpassword123",
        "is_superuser": False,
    }
    response = await client.post("/api/v1/auth/register", json=reg_data)
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["email"] == "register@example.com"
    assert "id" in json_data

    # Test duplicate registration
    response = await client.post("/api/v1/auth/register", json=reg_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_user_login(client: AsyncClient) -> None:
    # Register first
    reg_data = {
        "email": "login@example.com",
        "password": "mypassword123",
        "is_superuser": False,
    }
    await client.post("/api/v1/auth/register", json=reg_data)

    # Valid Login
    login_data = {"username": "login@example.com", "password": "mypassword123"}
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Invalid Password Login
    invalid_password_data = {
        "username": "login@example.com",
        "password": "wrongpassword",
    }
    response = await client.post("/api/v1/auth/login", data=invalid_password_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect email or password"

    # Non-existent User Login
    nonexistent_data = {
        "username": "nonexistent@example.com",
        "password": "mypassword123",
    }
    response = await client.post("/api/v1/auth/login", data=nonexistent_data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_rbac_guards(client: AsyncClient, db_session: AsyncSession) -> None:
    # 1. Unauthenticated request -> 401 Unauthorized
    response = await client.get("/api/v1/protected")
    assert response.status_code == 401

    # Register normal user
    reg_data = {
        "email": "normal@example.com",
        "password": "mypassword123",
        "is_superuser": False,
    }
    await client.post("/api/v1/auth/register", json=reg_data)

    # Login
    login_data = {"username": "normal@example.com", "password": "mypassword123"}
    login_resp = await client.post("/api/v1/auth/login", data=login_data)
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Authenticated but lacks permissions -> 403 Forbidden
    response = await client.get("/api/v1/protected", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

    # 3. Superuser bypass -> 200 OK
    admin_data = {
        "email": "admin@example.com",
        "password": "adminpassword123",
        "is_superuser": True,
    }
    await client.post("/api/v1/auth/register", json=admin_data)

    admin_login = {
        "username": "admin@example.com",
        "password": "adminpassword123",
    }
    admin_login_resp = await client.post("/api/v1/auth/login", data=admin_login)
    admin_access_token = admin_login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_access_token}"}

    response = await client.get("/api/v1/protected", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"

    # 4. User with matched RBAC roles -> 200 OK
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)
    perm_repo = PermissionRepository(db_session)

    # Create permission & role
    perm = await perm_repo.create(
        {"name": "document:upload", "description": "Can upload documents"}
    )
    role = await role_repo.create(
        {"name": "uploader", "description": "Document uploader"}
    )

    # Load user and role with relationships eager loaded
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from backend.models.auth import User

    user_stmt = (
        select(User)
        .where(User.email == "normal@example.com")
        .options(selectinload(User.roles))
    )
    user_result = await db_session.execute(user_stmt)
    normal_user = user_result.scalars().one()

    role_stmt = (
        select(Role).where(Role.id == role.id).options(selectinload(Role.permissions))
    )
    role_result = await db_session.execute(role_stmt)
    role_loaded = role_result.scalars().one()

    # Link permission and role
    role_loaded.permissions.append(perm)
    await role_repo.update(role_loaded, role_loaded)

    # Link role and user
    normal_user.roles.append(role_loaded)
    await user_repo.update(normal_user, normal_user)
    await db_session.commit()

    # Re-request as normal user (now possessing roles & permissions)
    response = await client.get("/api/v1/protected", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "normal@example.com"


@pytest.mark.asyncio
async def test_token_refresh_and_expired_handling(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Register & Login to get token
    reg_data = {
        "email": "refresh@example.com",
        "password": "mypassword123",
        "is_superuser": False,
    }
    await client.post("/api/v1/auth/register", json=reg_data)

    login_data = {"username": "refresh@example.com", "password": "mypassword123"}
    login_resp = await client.post("/api/v1/auth/login", data=login_data)
    tokens = login_resp.json()
    refresh_token = tokens["refresh_token"]

    # 1. Valid Token Refresh
    refresh_data = {"refresh_token": refresh_token}
    response = await client.post("/api/v1/auth/refresh", json=refresh_data)
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["refresh_token"] != refresh_token

    # 2. Expired Token Refresh -> 401 Unauthorized
    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_email("refresh@example.com")
    assert user is not None

    # Generate an expired refresh token manually
    expired_token = create_refresh_token(
        subject=user.id, expires_delta=timedelta(seconds=-10)
    )

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": expired_token}
    )
    assert response.status_code == 401

    # 3. Invalid Token Refresh -> 401 Unauthorized
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-valid-token"}
    )
    assert response.status_code == 401
