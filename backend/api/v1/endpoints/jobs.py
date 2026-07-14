from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import check_permissions, get_active_user, get_db
from backend.models.auth import User
from backend.models.jobs import Evaluation, TrainingJob
from backend.schemas.jobs import (
    ActiveDeploymentUpdate,
    DeploymentOut,
    EvaluationOut,
    TrainingJobCreate,
    TrainingJobOut,
)
from backend.services.deployment import get_active_adapter, set_active_adapter

router = APIRouter()


@router.post("", response_model=TrainingJobOut, status_code=status.HTTP_201_CREATED)
async def create_training_job(
    payload: TrainingJobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        check_permissions("document:upload")
    ),  # Only administrators or privileged users
) -> Any:
    """Enqueues a new model fine-tuning QLoRA job."""
    # Define a clean custom model name or default
    import uuid

    job_id = uuid.uuid4()
    model_name = f"hermes-qlora-{str(job_id)[:8]}"

    job = TrainingJob(
        id=job_id,
        user_id=current_user.id,
        model_name=model_name,
        base_model=payload.base_model,
        dataset_path=payload.dataset_path,
        hyperparameters=payload.hyperparameters or {},
        status="pending",
        is_active=False,
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Trigger background celery task
    from backend.celery_worker.tasks import train_model_task

    train_model_task.delay(str(job.id))

    return job


@router.get("", response_model=list[TrainingJobOut])
async def list_training_jobs(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_active_user),
) -> Any:
    """Lists all historical and active model training jobs."""
    stmt = select(TrainingJob).order_by(TrainingJob.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/evaluations", response_model=list[EvaluationOut])
async def list_evaluations(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_active_user),
) -> Any:
    """Lists all compiled benchmark model evaluations."""
    stmt = select(Evaluation).order_by(Evaluation.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/deployments", response_model=list[DeploymentOut])
async def list_deployments(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_active_user),
) -> Any:
    """Returns available deployment targets: base model and completed runs."""
    deployments = []

    # 1. Fetch current active adapter name
    active_name = get_active_adapter()

    # 2. Add base model default
    from backend.core.config import settings

    base_path = settings.models.llm_model
    deployments.append(
        DeploymentOut(
            name="Base Model Default",
            id="base",
            path=base_path,
            is_active=(active_name == base_path or active_name == "base"),
        )
    )

    # 3. Add all successfully completed training adapters
    stmt = select(TrainingJob).where(TrainingJob.status == "completed")
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    for job in jobs:
        deployments.append(
            DeploymentOut(
                name=f"Fine-tuned Adapter ({job.model_name})",
                id=str(job.id),
                path=job.model_name,
                is_active=(active_name == job.model_name),
            )
        )

    return deployments


@router.post("/deployments/active", status_code=status.HTTP_200_OK)
async def activate_deployment(
    payload: ActiveDeploymentUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(check_permissions("document:upload")),
) -> Any:
    """Selects and sets the active adapter loaded by the model service."""
    # 1. Update the database state (turn off all is_active, set target to True)
    from backend.core.config import settings

    target = payload.model_name

    # Reset all to False
    await db.execute(update(TrainingJob).values(is_active=False))

    # Mark the targeted job as active
    if target not in ["base", "default", settings.models.llm_model]:
        stmt = select(TrainingJob).where(
            TrainingJob.model_name == target, TrainingJob.status == "completed"
        )
        res = await db.execute(stmt)
        job = res.scalars().first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Completed training job with model name '{target}' not found.",
            )
        job.is_active = True

    await db.commit()

    # 2. Update the in-memory active adapter routing path
    set_active_adapter(target)

    return {"status": "success", "active_model": get_active_adapter()}


@router.get("/deployments/active")
async def get_active_deployment_route(
    _current_user: User = Depends(get_active_user),
) -> Any:
    """Returns the current routing target model/adapter name."""
    return {"active_model": get_active_adapter()}


@router.get("/{job_id}", response_model=TrainingJobOut)
async def get_training_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_active_user),
) -> Any:
    """Fetches full details of a specific fine-tuning training job."""
    job = await db.get(TrainingJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training job not found.",
        )
    return job
