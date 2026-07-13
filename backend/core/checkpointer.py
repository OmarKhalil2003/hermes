import pickle
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_metadata,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models.checkpoint import (
    CheckpointBlobModel,
    CheckpointModel,
    CheckpointWriteModel,
)


class SQLAlchemyCheckpointSaver(BaseCheckpointSaver[str]):
    """LangGraph checkpointer that persists graph state in PostgreSQL via SQLAlchemy."""

    def __init__(
        self,
        async_session_factory: async_sessionmaker[AsyncSession],
        *,
        serde: Any | None = None,
    ) -> None:
        super().__init__(serde=serde)
        self.async_session_factory = async_session_factory

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Synchronous get_tuple is not implemented for async checkpointer."""
        raise NotImplementedError("Use async aget_tuple instead.")

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,  # noqa: A002
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        """Synchronous list is not implemented for async checkpointer."""
        raise NotImplementedError("Use async alist instead.")

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Synchronous put is not implemented for async checkpointer."""
        raise NotImplementedError("Use async aput instead.")

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Synchronous put_writes is not implemented for async checkpointer."""
        raise NotImplementedError("Use async aput_writes instead.")

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Asynchronously retrieve a checkpoint.

        Uses thread_id, checkpoint_ns, and checkpoint_id.
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id")

        async with self.async_session_factory() as session:
            if checkpoint_id:
                stmt = select(CheckpointModel).where(
                    CheckpointModel.thread_id == thread_id,
                    CheckpointModel.checkpoint_ns == checkpoint_ns,
                    CheckpointModel.checkpoint_id == checkpoint_id,
                )
            else:
                stmt = (
                    select(CheckpointModel)
                    .where(
                        CheckpointModel.thread_id == thread_id,
                        CheckpointModel.checkpoint_ns == checkpoint_ns,
                    )
                    .order_by(CheckpointModel.created_at.desc())
                    .limit(1)
                )

            res = await session.execute(stmt)
            row = res.scalar_one_or_none()
            if not row:
                return None

            # Deserialize checkpoint data
            checkpoint_data = pickle.loads(row.checkpoint_data)
            checkpoint = self.serde.loads_typed(checkpoint_data)

            # Deserialize metadata
            metadata_data = pickle.loads(row.metadata_data)
            metadata = self.serde.loads_typed(metadata_data)

            # Populate channel_values from blobs table
            checkpoint["channel_values"] = {}
            blob_stmt = select(CheckpointBlobModel).where(
                CheckpointBlobModel.thread_id == thread_id,
                CheckpointBlobModel.checkpoint_ns == checkpoint_ns,
            )
            blob_res = await session.execute(blob_stmt)
            blobs = blob_res.scalars().all()
            blob_map = {
                (b.channel, b.version): (b.type_name, b.blob_data) for b in blobs
            }

            for k, v in checkpoint.get("channel_versions", {}).items():
                blob_key = (k, v)
                if blob_key in blob_map:
                    type_name, blob_data = blob_map[blob_key]
                    if type_name != "empty":
                        checkpoint["channel_values"][k] = self.serde.loads_typed(
                            (type_name, blob_data)
                        )

            # Load pending writes
            writes_stmt = select(CheckpointWriteModel).where(
                CheckpointWriteModel.thread_id == thread_id,
                CheckpointWriteModel.checkpoint_ns == checkpoint_ns,
                CheckpointWriteModel.checkpoint_id == row.checkpoint_id,
            )
            writes_res = await session.execute(writes_stmt)
            writes = writes_res.scalars().all()

            pending_writes = []
            for w in writes:
                val = self.serde.loads_typed((w.type_name, w.blob_data))
                pending_writes.append((w.task_id, w.channel, val))

            parent_config: RunnableConfig | None = None
            if row.parent_checkpoint_id:
                parent_config = cast(
                    RunnableConfig,
                    {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": row.parent_checkpoint_id,
                        }
                    },
                )

            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row.checkpoint_id,
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
                pending_writes=pending_writes,
            )

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Asynchronously save a checkpoint."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        c = dict(checkpoint).copy()
        values = cast(dict[str, Any], c.pop("channel_values", {}))

        async with self.async_session_factory() as session:
            # 1. Upsert blobs
            for k, v in new_versions.items():
                if k in values:
                    type_name, blob_data = self.serde.dumps_typed(values[k])
                else:
                    type_name, blob_data = "empty", b""

                blob_stmt = select(CheckpointBlobModel).where(
                    CheckpointBlobModel.thread_id == thread_id,
                    CheckpointBlobModel.checkpoint_ns == checkpoint_ns,
                    CheckpointBlobModel.channel == k,
                    CheckpointBlobModel.version == v,
                )
                blob_res = await session.execute(blob_stmt)
                blob_row = blob_res.scalar_one_or_none()

                if blob_row:
                    blob_row.type_name = type_name
                    blob_row.blob_data = blob_data
                else:
                    session.add(
                        CheckpointBlobModel(
                            thread_id=thread_id,
                            checkpoint_ns=checkpoint_ns,
                            channel=k,
                            version=v,
                            type_name=type_name,
                            blob_data=blob_data,
                        )
                    )

            # 2. Upsert checkpoint
            checkpoint_data = pickle.dumps(self.serde.dumps_typed(c))
            metadata_data = pickle.dumps(
                self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))
            )

            stmt = select(CheckpointModel).where(
                CheckpointModel.thread_id == thread_id,
                CheckpointModel.checkpoint_ns == checkpoint_ns,
                CheckpointModel.checkpoint_id == checkpoint_id,
            )
            res = await session.execute(stmt)
            row = res.scalar_one_or_none()

            if row:
                row.parent_checkpoint_id = parent_checkpoint_id
                row.checkpoint_data = checkpoint_data
                row.metadata_data = metadata_data
            else:
                session.add(
                    CheckpointModel(
                        thread_id=thread_id,
                        checkpoint_ns=checkpoint_ns,
                        checkpoint_id=checkpoint_id,
                        parent_checkpoint_id=parent_checkpoint_id,
                        checkpoint_data=checkpoint_data,
                        metadata_data=metadata_data,
                    )
                )

            await session.commit()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Asynchronously save pending writes."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]

        async with self.async_session_factory() as session:
            for idx, (c, v) in enumerate(writes):
                type_name, blob_data = self.serde.dumps_typed(v)

                write_stmt = select(CheckpointWriteModel).where(
                    CheckpointWriteModel.thread_id == thread_id,
                    CheckpointWriteModel.checkpoint_ns == checkpoint_ns,
                    CheckpointWriteModel.checkpoint_id == checkpoint_id,
                    CheckpointWriteModel.task_id == task_id,
                    CheckpointWriteModel.idx == idx,
                )
                res = await session.execute(write_stmt)
                row = res.scalar_one_or_none()

                if row:
                    row.channel = c
                    row.type_name = type_name
                    row.blob_data = blob_data
                    row.task_path = task_path
                else:
                    session.add(
                        CheckpointWriteModel(
                            thread_id=thread_id,
                            checkpoint_ns=checkpoint_ns,
                            checkpoint_id=checkpoint_id,
                            task_id=task_id,
                            idx=idx,
                            channel=c,
                            type_name=type_name,
                            blob_data=blob_data,
                            task_path=task_path,
                        )
                    )

            await session.commit()

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,  # noqa: A002, ARG002
        before: RunnableConfig | None = None,  # noqa: ARG002
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """Asynchronously list checkpoints."""
        if config is None:
            stmt = select(CheckpointModel)
        else:
            thread_id = config["configurable"]["thread_id"]
            checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
            stmt = select(CheckpointModel).where(
                CheckpointModel.thread_id == thread_id,
                CheckpointModel.checkpoint_ns == checkpoint_ns,
            )

        stmt = stmt.order_by(CheckpointModel.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)

        async with self.async_session_factory() as session:
            res = await session.execute(stmt)
            rows = res.scalars().all()

            for row in rows:
                conf = {
                    "configurable": {
                        "thread_id": row.thread_id,
                        "checkpoint_ns": row.checkpoint_ns,
                        "checkpoint_id": row.checkpoint_id,
                    }
                }
                tup = await self.aget_tuple(cast(RunnableConfig, conf))
                if tup:
                    yield tup

    async def adelete_thread(self, thread_id: str) -> None:
        """Asynchronously delete thread checkpoints."""
        async with self.async_session_factory() as session:
            await session.execute(
                delete(CheckpointModel).where(CheckpointModel.thread_id == thread_id)
            )
            await session.execute(
                delete(CheckpointBlobModel).where(
                    CheckpointBlobModel.thread_id == thread_id
                )
            )
            await session.execute(
                delete(CheckpointWriteModel).where(
                    CheckpointWriteModel.thread_id == thread_id
                )
            )
            await session.commit()
