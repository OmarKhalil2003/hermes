from __future__ import annotations

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class CheckpointModel(Base, TimestampMixin):
    """Database model to persist LangGraph checkpoints."""

    __tablename__ = "langgraph_checkpoints"

    thread_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    checkpoint_ns: Mapped[str] = mapped_column(
        String(255), primary_key=True, default=""
    )
    checkpoint_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    parent_checkpoint_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checkpoint_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    metadata_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class CheckpointBlobModel(Base, TimestampMixin):
    """Database model to persist LangGraph checkpoint blobs (channel values)."""

    __tablename__ = "langgraph_checkpoint_blobs"

    thread_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    checkpoint_ns: Mapped[str] = mapped_column(
        String(255), primary_key=True, default=""
    )
    channel: Mapped[str] = mapped_column(String(255), primary_key=True)
    version: Mapped[str] = mapped_column(String(255), primary_key=True)
    type_name: Mapped[str] = mapped_column(String(255), nullable=False)
    blob_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class CheckpointWriteModel(Base, TimestampMixin):
    """Database model to persist pending checkpoint writes."""

    __tablename__ = "langgraph_checkpoint_writes"

    thread_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    checkpoint_ns: Mapped[str] = mapped_column(
        String(255), primary_key=True, default=""
    )
    checkpoint_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    idx: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(255), nullable=False)
    type_name: Mapped[str] = mapped_column(String(255), nullable=False)
    blob_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    task_path: Mapped[str] = mapped_column(String(255), default="")
