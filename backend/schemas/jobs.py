from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrainingJobCreate(BaseModel):
    """Schema payload to queue a new QLoRA fine-tuning training job."""

    base_model: str = Field(
        default="Qwen/Qwen2.5-3B-Instruct",
        description="The base causal model to load.",
    )
    dataset_path: str = Field(
        default="finetuning/dataset.jsonl",
        description="Path to the JSONL dataset file on disk.",
    )
    hyperparameters: dict[str, Any] | None = Field(
        default=None,
        description="Optional hyperparameter overrides (epochs, batch_size, etc.).",
    )


class TrainingJobOut(BaseModel):
    """Schema output returning details of a training job."""

    id: UUID
    user_id: UUID
    model_name: str
    base_model: str
    dataset_path: str
    hyperparameters: dict[str, Any] | None
    status: str
    mlflow_run_id: str | None
    error_message: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationOut(BaseModel):
    """Schema output returning model evaluations."""

    id: UUID
    training_job_id: UUID | None
    model_name: str
    dataset_name: str
    metrics: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActiveDeploymentUpdate(BaseModel):
    """Payload targeting active model deployment routing changes."""

    model_name: str = Field(
        description="The target model adapter or base model name to activate."
    )


class DeploymentOut(BaseModel):
    """Schema returning detailed deployment target information."""

    name: str = Field(description="Display name of the deployment target.")
    id: str = Field(description="Identifier (job UUID or 'base').")
    path: str = Field(description="Reference name/path for the model service.")
    is_active: bool = Field(description="True if currently handling query traffic.")
