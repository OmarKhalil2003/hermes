from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from unittest.mock import patch
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.nodes import get_llm
from backend.celery_worker.tasks import train_model_task
from backend.models.auth import User
from backend.models.jobs import Evaluation, TrainingJob
from backend.services.deployment import get_active_adapter, set_active_adapter


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Fixture creating an admin user (superuser) with required permissions."""
    stmt = select(User).where(User.email == "admin@hermes.ai")
    res = await db_session.execute(stmt)
    existing = res.scalars().first()
    if existing:
        return existing

    user = User(
        email="admin@hermes.ai",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def override_auth(admin_user: User) -> Generator[None]:
    """Bypasses API security dependencies for active user testing."""
    from backend.api.deps import check_permissions, get_active_user
    from backend.main import app

    app.dependency_overrides[get_active_user] = lambda: admin_user
    app.dependency_overrides[check_permissions("document:upload")] = lambda: admin_user
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.usefixtures("override_auth")
async def test_deployment_endpoints(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verifies available deployments endpoints listing and selection."""
    # Ensure active adapter is default base model initially
    set_active_adapter(None)

    # 1. Start a training job
    payload = {
        "base_model": "sshleifer/tiny-gpt2",
        "dataset_path": "finetuning/dataset.jsonl",
        "hyperparameters": {"epochs": 1, "batch_size": 1, "lora_r": 4, "max_steps": 1},
    }

    with patch("backend.celery_worker.tasks.train_model_task.delay") as mock_delay:
        response = await client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert "id" in data
        job_id = data["id"]
        mock_delay.assert_called_once_with(job_id)

    # 2. Force mark job as completed in DB to enable deployment
    stmt = select(TrainingJob).where(TrainingJob.id == UUID(job_id))
    res = await db_session.execute(stmt)
    job = res.scalar_one()
    job.status = "completed"
    await db_session.commit()

    # 3. Retrieve deployments list
    response = await client.get("/api/v1/jobs/deployments")
    assert response.status_code == 200
    deploys = response.json()
    assert len(deploys) >= 2  # base model + completed job

    base_deploy = next(d for d in deploys if d["id"] == "base")
    custom_deploy = next(d for d in deploys if d["id"] == job_id)

    assert base_deploy["is_active"] is True
    assert custom_deploy["is_active"] is False

    # 4. Activate custom adapter deployment
    response = await client.post(
        "/api/v1/jobs/deployments/active", json={"model_name": custom_deploy["path"]}
    )
    assert response.status_code == 200
    assert response.json()["active_model"] == custom_deploy["path"]
    assert get_active_adapter() == custom_deploy["path"]

    # 5. Retrieve active deployment details
    response = await client.get("/api/v1/jobs/deployments/active")
    assert response.status_code == 200
    assert response.json()["active_model"] == custom_deploy["path"]

    # 6. Verify LLM factory uses the active adapter path
    llm = get_llm()
    assert llm.model_name == custom_deploy["path"]

    # Clean up
    set_active_adapter(None)


@pytest.mark.asyncio
async def test_celery_train_model_task(
    db_session: AsyncSession, admin_user: User
) -> None:
    """Verifies that the Celery training task correctly runs the pipeline."""
    # 1. Create a pending job
    job = TrainingJob(
        user_id=admin_user.id,
        model_name="hermes-qlora-test",
        base_model="sshleifer/tiny-gpt2",
        dataset_path="finetuning/dataset.jsonl",
        hyperparameters={"epochs": 1, "max_steps": 1},
        status="pending",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # 2. Run the Celery task (mocking training implementation dependencies
    # to avoid full HuggingFace model loads)
    @asynccontextmanager
    async def mock_session_factory() -> AsyncGenerator[AsyncSession]:
        yield db_session

    with (
        patch(
            "backend.celery_worker.tasks.async_session_factory",
            mock_session_factory,
        ),
        patch("finetuning.train.train_model") as mock_train,
    ):
        result_msg = train_model_task(str(job.id))
        assert "completed successfully" in result_msg
        mock_train.assert_called_once()

    # 3. Verify job status updated in DB
    await db_session.refresh(job)
    assert job.status == "completed"

    # 4. Verify evaluation entry was compiled and linked
    stmt = select(Evaluation).where(Evaluation.training_job_id == job.id)
    res = await db_session.execute(stmt)
    evaluation = res.scalar_one_or_none()
    assert evaluation is not None
    assert evaluation.model_name == job.model_name
    assert "rouge1" in evaluation.metrics
    assert evaluation.metrics["rouge1"] > 0.0
